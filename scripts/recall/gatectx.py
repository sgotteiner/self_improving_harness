"""What the gate's lessons check sees besides the turn: his message, the assistant's reply before it, and the kind the
message step detected for the message (stored per transcript by delegate.input_step). Stdlib only."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

NONE = "(not detected)"
NOTIFIED = ("(none: this turn started from a background agent's completion notice, not from a message of his. The reply answers that "
            "agent's result, so lessons about answering his question or what he wants to know do not apply; judge only the reply's own claims.)")


def _file(tp):
    return os.path.join(os.path.dirname(ctx.LOG), "kind-" + os.path.basename(tp or "x") + ".txt")


def save_kind(tp, prompt, kind):
    """Remember the kind detected for this message; the first line is the kind, the rest is the message it belongs to."""
    if tp:
        open(_file(tp), "w", encoding="utf-8").write(kind + "\n" + prompt.strip())


def load_kind(tp, prompt):
    """The stored kind if it was detected for this very message, else NONE."""
    try:
        kind, _, saved = open(_file(tp), encoding="utf-8").read().partition("\n")
        return kind if saved.strip() == prompt.strip() else NONE
    except OSError:
        return NONE


def around(tp):
    """(his latest message, the assistant's text before it, its detected kind); "(none)" for a part that is missing."""
    es = ctx.entries(tp, notices=True)  # the queued-command notices too, so a turn that began from one is seen
    hs = [i for i, e in enumerate(es) if ctx.human_text(e)]
    if not hs:
        return "(none)", "(none)", NONE
    if any(ctx._notice(e) for e in es[hs[-1] + 1:]):
        return NOTIFIED, "(none)", NONE
    msg = ctx.human_text(es[hs[-1]]).strip()
    lo = hs[-2] + 1 if len(hs) > 1 else 0
    prev = "\n".join(b["text"] for e in es[lo:hs[-1]] if e["type"] == "assistant" for b in ctx.blocks(e) if b.get("type") == "text")
    return msg, prev.strip() or "(none)", load_kind(tp, msg)
