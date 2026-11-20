"""Learning from the work: a detached background review of the stretch of a session since the last review. hook.py calls start() on
his message; a review is due when the message step flagged DONE, or LEARN_TURNS human turns passed since the last review. One brain
call drafts at most ONE lesson from how the work went (where it got stuck, what fixed it, an approach he approved), or NONE. A draft
goes through patchfirst (SAME -> edit proposal of that lesson, NEW -> new-lesson proposal; situation source "work"), so it reaches
him only as the proposal line. Slot `work-learning`. One run at a time; state in results/work_review.json. Fails open.
Usage: python -I scripts/recall/workreview.py run <transcript>   (reviews now, prints the draft)"""
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clean, ctx
from workstretch import stretch  # noqa: the scrubbed stretch text
from workstate import change, cut, captured, humans, path, read  # noqa: the state and its marks live in workstate.py

LEARN_TURNS = 10  # human turns since the last review that make one due
RUN_STALE_MIN = 30  # a run marked running this long ago is taken as crashed
RETRIES = 5  # tries to release the run when the state lock is busy
PROMPT = ("The stretch of a coding session between an owner (O) and his AI assistant (A), with its tool calls (T) and their results "
          "(R):\n{work}\n\nDraft AT MOST ONE lesson the assistant should learn from how this work went: where it got stuck and what "
          "fixed it, or an approach the owner approved. It must be a general principle that will matter again, not a detail of this "
          "project. If nothing in it is worth a lesson, reply exactly NONE. Otherwise reply with exactly these lines, in general "
          "words, no names, paths or file names:\nSITUATION: <the context and what was being done>\nDID: <what the assistant did>\n"
          "OUTCOME: <what happened: the snag and its fix, or what the owner approved>\nLESSON: <one general sentence>\n"
          "SLUG: <2-4 words, kebab-case>")
FIELDS = ("SITUATION", "DID", "OUTCOME", "LESSON", "SLUG")


def due(tp, done, s=None):
    """Is a review due for this session: DONE was flagged, or LEARN_TURNS human turns passed since the last review of it."""
    last = (read() if s is None else s).get(tp, {})
    return bool(done) or humans(ctx.entries(tp)) - last.get("humans", 0) >= LEARN_TURNS


def parse(out):
    """{SITUATION, DID, OUTCOME, LESSON, SLUG} from the brain's reply, or None (NONE, or a field missing)."""
    if out.strip().upper().startswith("NONE"):
        return None
    d = {k: (re.search(rf"^\W*{k}\s*:\s*(.+)$", out, re.M | re.I) or [None, ""])[1].strip(" `*") for k in FIELDS}
    return d if all(d.values()) else None


def review(tp, marks, es):
    """Review the stretch since the last review up to the cut `marks`, queue at most one draft. Returns the draft dict, or None.
    Skipped (no brain call) when capture recorded an occurrence or a proposal in this stretch: it already holds the lesson.
    Raises on a failed call."""
    import brain, patchfirst
    prev = read().get(tp, {})
    if captured(prev, marks):
        ctx.log("workreview: skipped, capture recorded an occurrence or a proposal from this stretch")
        return None
    work = stretch(tp, prev.get("entries", 0), marks["entries"], es)
    if not work.strip():
        return None
    out, _ = brain.ask(PROMPT.format(work=work), tag="work-review")
    d = parse(out)
    if not d:
        return None
    bad = [f"{k}: {v}" for k in ("SITUATION", "DID", "OUTCOME", "LESSON", "SLUG") for v in clean.violations(d[k], strict=True)]
    if bad:
        ctx.log(f"workreview: draft dropped, privacy scan: {bad}")
        return None
    c = json.dumps({"situation": d["SITUATION"], "assistant_did": d["DID"], "disliked": d["OUTCOME"]})
    patchfirst.propose({"situation": d["SITUATION"], "did": d["DID"], "disliked": d["OUTCOME"], "lesson": d["LESSON"], "slug": d["SLUG"]},
                       "work", d["OUTCOME"], c)
    return d


def release(tp, marks):
    """Mark the stretch reviewed (up to the cut) and clear `running`; retried while the lock is busy, then written without it.
    Returns the transcript of a DONE that came in while this ran (the run is claimed for it), else None."""
    def mark(s):
        s.pop("running", None)
        marks and s.__setitem__(tp, marks)
        again = s.pop("again", None)
        again and s.__setitem__("running", time.time())
        return again
    for _ in range(RETRIES):
        try:
            return change(mark)
        except OSError:
            time.sleep(0.5)
    s = read()  # last resort: a stuck `running` would block every later review for RUN_STALE_MIN
    out = mark(s)
    open(path(), "w", encoding="utf-8").write(json.dumps(s, indent=1, sort_keys=True))
    return out


def run(tp):
    """One review as the detached process does it: the stretch (as cut before the call) is marked reviewed whatever came out (a
    failed call is logged and the stretch is not retried), the run is released, and a DONE that waited is run now."""
    marks = None
    try:
        es = ctx.entries(tp)
        marks = cut(tp, es)  # the stretch ends here; what comes in during the call belongs to the next one
        return review(tp, marks, es)
    except Exception as e:
        ctx.log(f"workreview: failed: {e!r}")
    finally:
        again = release(tp, marks)
        again and spawn(again)


def spawn(tp):
    flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
    with open(ctx.LOG, "a", encoding="utf-8") as err:
        subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "run", tp], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=err, creationflags=flags, close_fds=True)


def start(tp, done):
    """Called by the hook: spawn a review when one is due and none is running; a DONE that finds one running is remembered and run
    after it. Never raises."""
    try:
        if not (ctx.enabled("work-learning") and ctx.enabled("capture")) or not tp:
            return False
        if tp not in read():  # the marks the stretch of a new session is measured from
            m = cut(tp, [])
            change(lambda s: s.setdefault(tp, m))
        if not due(tp, done):
            return False
        def claim(s):
            if time.time() - s.get("running", 0) < RUN_STALE_MIN * 60:
                done and s.__setitem__("again", tp)
                return False
            s["running"] = time.time()
            return True
        if not change(claim):
            return False
        spawn(tp)
        return True
    except Exception as e:
        ctx.log(f"workreview: not started: {e!r}")
        return False


if __name__ == "__main__" and sys.argv[1:2] == ["run"]:
    print(run(sys.argv[2]) or "NONE")
