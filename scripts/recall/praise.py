"""Success capture, the praise half of the message step's one call (delegate.input_step; no second call). With slot `success-capture`
on, the prompt gets ASK: the model adds a line `PRAISE | <what he liked>` when his message praises anything the setup did in the recent
turns (the assistant, an agent, a hook, a gate catch). take() cuts that line out (so the kind and the flags are read as before) and returns its sentence, the detector's guess;
capwrite.success_instruction turns it into the line the session sees. Off = no ask, nothing cut."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flagline

SLOT = "success-capture"
FLAG = "PRAISE"
ASK = (f"\n\nOn the flags line also add, when his message praises or says he liked something that the assistant, one of its agents, "
       f"a hook or a gate catch did in the recent turns (not only the previous one), exactly one line starting with {FLAG}: "
       f"`{FLAG} | <score> | <one sentence naming what he liked>`, <score> = how sure you are that he praised the assistant, 1 to 5 (1 = a guess, 5 = certain). Otherwise add no such line.")
LINE = flagline.regex(FLAG)


def ask():
    return flagline.ask(SLOT, ASK)


def take(out):
    """-> (out without its PRAISE line, its sentence or "")."""
    return flagline.take(SLOT, LINE, out)
