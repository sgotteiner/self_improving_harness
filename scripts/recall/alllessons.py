"""Slot recall-all-lessons: the cheap model sees EVERY approved lesson on each call and names the ones that apply (any number),
instead of embedding retrieval picking candidates. Used by hook.py (his message) and gate.py (the turn). Stdlib only."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, views

LESSONS_MAX = 12000  # chars of the lessons text; above it we log and still send it all (no silent cut): time to switch the slot off
NAMED_MAX = 5  # at most this many lessons reach the main session per call; more are logged, so its context stays small

RECALL = ("Recent turns of a coding session:\n{ctx}\n\nOwner's new message: {prompt}\n\nLessons from earlier mistakes of this "
          "assistant:\n{lessons}\n\nWhich lessons clearly apply to what is going on now, so that repeating the old mistake is a real "
          "risk? Any number, none is fine. Be strict: when unsure, leave it out. Reply 'NONE' or one line per lesson that applies: "
          "<id> | <why it applies, one factual sentence>.")
GATE = ("Lessons from earlier mistakes of this assistant:\n{lessons}\n\nContext.\nThe assistant's previous reply (before the owner's "
        "message):\n{prev}\n\nThe owner's message: {message}\nThe kind the message step detected for it: {kind}\n\n"
        "The assistant's latest turn, the one to judge.\nTool calls this turn:\n{tools}"
        "\n\nFinal message:\n{text}\n\nEvidence from the previous reply or from output the owner already saw (e.g. the message "
        "step's own output) counts, not only this turn's tool calls. Judge whether the turn answered what he asked against his "
        "actual message and its kind. Which lessons does this turn CLEARLY violate (e.g. claims something works or is done with no "
        "run of a test or the app in the tool calls or the context)? Be strict: unclear or merely possible -> not a violation. Reply "
        "'OK' or one line per clearly broken lesson: 'VIOLATION <id> | <one short sentence: what is wrong and what to do now>'.")


lessons = views.lessons  # {id: (date, lesson, right)} of every approved case


def block(ls):
    text = "\n".join(f"- {c}: Lesson: {l} Right: {r}" for c, (_, l, r) in ls.items())
    if len(text) > LESSONS_MAX:
        ctx.log(f"alllessons: lessons text is {len(text)} chars, over {LESSONS_MAX}; sent whole")
    return text


def named(out, ls, head=""):
    """[(id, why)] from the model's lines `<head><id> | <why>` whose id is a known lesson, each id once."""
    got = {}
    for l in out.splitlines():
        l = l.strip(" -*`")
        if head:
            if not l.startswith(head):
                continue
            l = l[len(head):]
        cid, _, why = [x.strip(" -*`") for x in l.partition("|")]
        if cid in ls and cid not in got:
            got[cid] = why
    if len(got) > NAMED_MAX:
        ctx.log(f"alllessons: model named {len(got)} lessons, kept the first {NAMED_MAX}: {', '.join(list(got)[NAMED_MAX:])} dropped")
    return list(got.items())[:NAMED_MAX]
