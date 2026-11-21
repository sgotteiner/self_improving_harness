"""The done question, a half of the message step's one call (delegate.input_step; no second call). The prompt gets ASK (read from
tasks/delegation-draft.md, "Done question"): when his message asks whether the work is done or everything is fixed, the model adds a
line `DONE-ASK | <score> | <why>`. take() cuts it out (so the DONE flag never reads it) and says whether he surely asked (score 4-5,
relevance.py); line() is the instruction with the full leftover list (leftovers.py) attached. Rides on slot delegation-hook."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, diary, flagline, relevance

SLOT = "delegation-hook"
FLAG = "DONE-ASK"
LINE = flagline.regex(FLAG)


def ask(prompt):
    """The text added to the message step's prompt; `prompt` = delegate._prompt."""
    return flagline.ask(SLOT, "\n\n" + prompt("Done question"))


def take(out, prompt):
    """-> (out without its DONE-ASK line, True when he surely asked whether it is done). Weak guesses are logged by relevance."""
    out, said = flagline.take(SLOT, LINE, out, keep_first=True)
    (sure,), _ = relevance.sort([said], prompt)
    return out, bool(sure) and relevance.split(said)[0] is not None  # no score: no list (a missed list costs nothing, a false one is noise)


def line(instruction, transcript):
    """The instruction plus the full leftover list of the session's project; the list failing is said, never left empty."""
    try:
        import leftovers
        return f"{instruction}\n{leftovers.report(diary.project_of(transcript) if transcript else '', transcript)}"
    except Exception as e:
        ctx.log(f"doneask: list failed: {e!r}")
        return f"{instruction}\n(the list could not be built; check the todo, the ideas and git status yourself)"
