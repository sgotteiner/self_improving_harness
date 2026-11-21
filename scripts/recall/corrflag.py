"""The correction flag, the third half of the message step's one call (delegate.input_step). With slot `capture` on, the prompt gets
ASK: any kind of message that also corrects the assistant gets a second line `CORRECTION | <the mistake>`, so a TASK that corrects
still gets the capture line. take() cuts that line out (never the kind line, the first one) and returns its sentence."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flagline

SLOT = "capture"
FLAG = "CORRECTION"
ASK = (f"\n\nWhatever kind you pick, when his message also says the assistant got something wrong or did not follow him, add "
       f"exactly one more line `{FLAG} | <one sentence naming the assistant's mistake>` (not for the kind line itself when the kind is "
       f"{FLAG}). Otherwise add no such line.")
LINE = flagline.regex(FLAG)


def ask():
    return flagline.ask(SLOT, ASK)


def take(out):
    """-> (out without its CORRECTION flag line, its sentence or ""). The first line (the kind) is left alone."""
    return flagline.take(SLOT, LINE, out, keep_first=True)
