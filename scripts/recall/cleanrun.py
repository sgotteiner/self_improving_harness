"""When the lessons' cleanup (cleanup.py) runs: hook.py calls start() on each message; a run is due every R.CLEANUP_DAYS (R.OVER_DAYS
while the lessons text is over its size limit), runs in a detached process, and only one run at a time (claimed in cleanstate.py's
file under its lock). A run that crashed or had a failing step is logged to hook.log and retried the next day; last_run is set only
by a run that succeeded. Fails open. Usage: python -I scripts/recall/cleanrun.py run   (runs now, prints what it queued)"""
import datetime, os, subprocess, sys, time, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cleanrules as R, cleanstate, cleanup, ctx, views


def running(s):
    return time.time() - s.get("running", 0) < R.RUN_STALE_MIN * 60


def due(today=None, s=None):
    """Is a run due: the last successful one is R.CLEANUP_DAYS old (R.OVER_DAYS while over the limit) and none crashed today."""
    today, s = today or str(datetime.date.today()), cleanstate.read() if s is None else s
    last = s.get("last_run")
    return s.get("last_fail") != today and (not last or R.age(last, today) >= (R.OVER_DAYS if cleanup.over(views.lessons()) else R.CLEANUP_DAYS))


def start():
    """Called by the hook: spawn a run when one is due (and proposals could be answered at all). Never raises. The run claims
    itself again, so two hooks spawning at once make one run; its stderr goes to hook.log."""
    try:
        if not (ctx.enabled("delegation-hook") and ctx.enabled("capture")) or running(cleanstate.read()) or not due():
            return
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
        with open(ctx.LOG, "a", encoding="utf-8") as err:
            subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "run", "auto"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=err, creationflags=flags, close_fds=True)
    except Exception as e:
        ctx.log(f"cleanup: not started: {e!r}")


def claim(auto):
    """Mark a run as started, in one locked change: False when another run is on, or (auto) none is due any more."""
    def mark(s):
        if running(s) or (auto and not due(s=s)):
            return False
        s["running"] = time.time()
        return True
    return cleanstate.change(mark)


def finish(ok):
    """The run is over: a successful one is last_run, a crashed or partly failed one is last_fail (retried the next day)."""
    def mark(s):
        s.pop("running", None)
        s["last_run" if ok else "last_fail"] = str(datetime.date.today())
    cleanstate.change(mark)


def main(auto=False):
    if not claim(auto):
        return []
    ok = False
    try:
        made, failed = cleanup.go(None)
        ok = not failed
        return made
    except BaseException:
        ctx.log("cleanup: run crashed:\n" + traceback.format_exc())
        raise
    finally:
        finish(ok)


if __name__ == "__main__" and sys.argv[1:2] == ["run"]:
    for kind, text in main(auto=sys.argv[2:] == ["auto"]):
        print(kind, "|", text)
