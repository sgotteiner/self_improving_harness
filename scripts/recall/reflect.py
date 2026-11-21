"""Reflection across sessions: every REFLECT_EVERY-th closed session of a project (SessionEnd hook) starts a detached run that reads
what those sessions recorded (the situations their feature traces link, with his corrections) and asks the brain one
question: does one mistake repeat across them, even when each time looked different or was filed under different lessons? It drafts
at most ONE lesson (or a reword) through workreview.queue / patchfirst with source "reflect", so it reaches him only as the proposal
line. Slot `reflection`. Closed sessions per project ({session id: transcript}) wait in work_review.json under "reflect"; the run uses workreview's one-run-at-
a-time mark (a crashed run is retried by the next close). Fails open.
Usage: SessionEnd hook (stdin)  |  python -I scripts/recall/reflect.py run <project> <transcript>...  (runs now, prints the draft)"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, workreview, workstate

SLOT = "reflection"
REFLECT_EVERY = 3  # closed sessions of a project that make a reflection due
WAITING_MAX = 30  # closed sessions kept waiting per project (a run takes the latest REFLECT_EVERY of them)
SITUATIONS_MAX = 40  # situations sent, the latest ones
SITUATION_CUT = 350  # chars kept of one situation line
TRACE_EACH, TRACE_MAX = 1800, 6000  # chars of one trace, of all traces sent
PROMPT = ("Material from {n} closed sessions of one coding project, between an owner and his AI assistant.\n\nSituations recorded in them "
          "(lesson id, source: what was going on | what the assistant did | outcome):\n{sits}\n\nFeature traces of these sessions, with "
          "his corrections:\n{traces}\n\nIs there ONE mistake of the assistant that repeats across these sessions, even if each time "
          "looked different or was filed under different lessons? A one-off, or a mistake that happened in only one session, does not "
          "count. If there is none, reply exactly NONE. Otherwise draft ONE lesson (or the general sentence a saved lesson should be "
          "reworded to) in general words, no names, paths or file names, as exactly these lines:\n" + workreview.REPLY)


def material(proj, tps):
    """(situations text, traces text) of these sessions."""
    import situations, tracing
    rows = [r for r in tracing.read(proj) if any(e.get("session") in tps for e in r["events"])]
    sids = {s for r in rows for e in r["events"] if e.get("session") in tps for s in e.get("sids", [])}  # the store has no project field: only what these sessions' traces link
    sits = [r for r in situations.read() if r["sid"] in sids and r["status"] == situations.ACTIVE][-SITUATIONS_MAX:]
    traces = "\n\n".join(tracing.render(r, TRACE_EACH) for r in rows)[:TRACE_MAX]
    return ("\n".join(f"- {r['lesson_id']}, {r['source']}: {r['situation']} | {r['did']} | {r['outcome']}"[:SITUATION_CUT] for r in sits) or "(none)",
            traces or "(none)")


def review(proj, tps):
    """One reflection over the sessions `tps`; queues at most one draft. Returns the draft dict or None. Raises on a failed call."""
    import brain
    sits, traces = material(proj, tps)
    if sits == traces == "(none)":
        return None
    out, _ = brain.ask(PROMPT.format(n=len(tps), sits=sits, traces=traces), tag="reflect")
    return workreview.queue(workreview.parse(out), "reflect")


def run(proj, tps):
    """The detached process: reflect, then release the run mark and drop the handled sessions from the waiting list."""
    try:
        return review(proj, tps)
    except Exception as e:
        ctx.log(f"reflect: failed: {e!r}")
    finally:
        again = workreview.release(None, None, lambda s: s.setdefault("reflect", {}).__setitem__(
            proj, {k: t for k, t in s["reflect"].get(proj, {}).items() if t not in tps}))
        again and workreview.spawn(again)  # a DONE review that waited for this run


def close(tp, sid=""):
    """A session closed: count it for its project (once per session id, a resumed or cleared session is not counted again); when
    REFLECT_EVERY wait and no run holds the mark, start one on the latest ones. Never raises."""
    try:
        import tracing
        if not (ctx.enabled(SLOT) and ctx.enabled("capture")) or not workstate.humans(ctx.entries(tp)):  # an empty session is not counted
            return False
        proj = tracing.project(tp)
        if not proj:
            return False
        def add(s):
            waiting = s.setdefault("reflect", {}).setdefault(proj, {})
            waiting.pop(sid or tp, None)  # a session that closes again moves to the end
            waiting[sid or tp] = tp
            for k in list(waiting)[:-WAITING_MAX]:  # only the cap drops one, never a run that is going
                del waiting[k]
            return list(waiting.values())[-REFLECT_EVERY:] if len(waiting) >= REFLECT_EVERY else []
        tps = workstate.change(add)
        if not tps or not workstate.change(workreview.claim):
            return False
        workreview.spawn(proj, *tps, script=os.path.abspath(__file__))
        return True
    except Exception as e:
        ctx.log(f"reflect: not started: {e!r}")
        return False


if __name__ == "__main__":
    if sys.argv[1:2] == ["run"]:
        print(run(sys.argv[2], sys.argv[3:]) or "NONE")
    elif not ctx.skip_env("RECALL_HOOK"):
        try:
            d = json.load(sys.stdin)
            close(d.get("transcript_path", ""), d.get("session_id", ""))
        except Exception as e:
            ctx.log(f"reflect: hook failed: {e!r}")
