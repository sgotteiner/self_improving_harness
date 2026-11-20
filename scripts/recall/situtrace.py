"""Situation tracing: when a lesson fires (his RIGHT verdict on a gate block, or a missed correction) one small call shows the
lesson's ACTIVE situations and the new case, and picks the closest: that situation gets hits+1 and last_hit today. None close ->
the case is a new kind: logged and noted in cleanstate.py (cleanup.py's reword rule reads it); a new situation of the case is
already linked to the lesson by history.record. No call when the lesson has no other active situation. Fails open. Stdlib only."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, cleanstate, ctx, situations

ASK = ("A lesson an AI coding assistant learned from its mistakes: {lesson}\n\nReal situations that led to it (id: situation):\n"
       "{items}\n\nA new case where this lesson fired:\n{case}\n\nWhich situation above is the closest to the new case (the same "
       "kind of mistake in a similar setting)? Reply with exactly one word: its id, or NEW when none of them is close.")


def fire(lesson_id, case, same=lambda r: False):
    """Trace a firing of lesson_id on `case` (text). same(row) is true for the row that IS this case (left out). Returns the
    sid hit, "NEW", or None (nothing to compare, or the call failed)."""
    try:
        rows = [r for r in situations.read() if r["lesson_id"] == lesson_id and r["status"] == situations.ACTIVE and not same(r)]
        if not rows:
            return None
        import views
        lesson = views.lessons().get(lesson_id, ("", "", ""))[1]
        out, _ = brain.ask(ASK.format(lesson=lesson, items="\n".join(f"{r['sid']}: {r['situation']}" for r in rows), case=case),
                           tag="situation-trace")
        word = (out.split() or [""])[0].strip("`*<>.,|:")
        if word in {r["sid"] for r in rows}:
            situations.hit(word)
            return word
        if word.upper() == "NEW":
            ctx.log(f"situtrace: new kind of case for {lesson_id}: {case[:100]}")
            cleanstate.note_new(lesson_id, case)
            return "NEW"
        ctx.log(f"situtrace: unreadable answer for {lesson_id}: {out[:60]!r}")
    except Exception as e:
        ctx.log(f"situtrace: {lesson_id} not traced: {e!r}")
    return None
