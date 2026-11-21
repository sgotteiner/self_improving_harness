"""Success capture, the praise half of the message step's one call (delegate.input_step; no second call). With slot `success-capture`
on, the prompt gets ASK: the model adds a line `PRAISE | <what he liked>` when his message praises the assistant's previous
turn. take() cuts that line out (so the kind and the flags are read as before) and returns its sentence, the detector's guess;
capwrite.success_instruction turns it into the line the session sees. Off = no ask, nothing cut."""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

SLOT = "success-capture"
FLAG = "PRAISE"
ASK = (f"\n\nOn the flags line also add, when his message praises or says he liked something the assistant did in its previous turn, "
       f"exactly one line starting with {FLAG}: `{FLAG} | <one sentence naming what he liked>`. Otherwise add no such line.")
LINE = re.compile(rf"^\W*{FLAG}\s*\|(.*)$", re.M | re.I)


def ask():
    """The text added to the message step's prompt ("" when the slot is off)."""
    return ASK if ctx.enabled(SLOT) else ""


def take(out):
    """-> (out without its PRAISE line, the sentence after it or "" when there is none or the slot is off)."""
    m = LINE.search(out) if ctx.enabled(SLOT) else None
    return (LINE.sub("", out), m.group(1).strip() or "not specified") if m else (out, "")
