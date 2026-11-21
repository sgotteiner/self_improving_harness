"""A flag line `FLAG | text` that the message step's one call may add after the kind line (praise.py, corrflag.py): the regex that finds
it, the prompt text gated on its slot, and the cut that returns its sentence."""
import re, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx


def regex(flag):
    return re.compile(rf"^\W*{flag}\s*\|(.*)$", re.M | re.I)


def ask(slot, text):
    """The text added to the message step's prompt ("" when the slot is off)."""
    return text if ctx.enabled(slot) else ""


def take(slot, line, out, keep_first=False):
    """-> (out without its flag line, the sentence after it or "" when there is none or the slot is off). keep_first: the first line
    (the kind) is never searched or cut."""
    head, nl, rest = out.lstrip().partition("\n") if keep_first else ("", "", out)
    m = line.search(rest) if ctx.enabled(slot) else None
    return (head + nl + line.sub("", rest), m.group(1).strip() or "not specified") if m else (out, "")
