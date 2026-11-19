"""Why the delegation gate's BLOCK must not stand: a fact counted from the transcript (or the brain's own hedge) says the
agent was called, the change is still being made, or it waits for its review. Used by delegate.output_step."""
import ctx

AGENT_OF = {"TESTER": "tester", "REVIEWER": "reviewer", "KNOWLEDGE-MANAGER": "knowledge-manager"}  # kind -> agent that answers it


def features(t):
    """The counted facts of a turn that decide a veto, as plain booleans and agent types: what a labelled false alarm is kept as
    (no words of his, no text of the turn)."""
    keys = ("called", "pending", "claims", "sm_ok", "fell_short", "round_started", "review_open", "suite_unexcused", "edited", "returned")
    return {k: t[k] for k in keys}


def veto(kind, reason, t):
    """Why the brain's BLOCK must not stand (a fact from the transcript or its own hedge says so), else None."""
    if AGENT_OF.get(kind) in t["called"]:
        return f"the {AGENT_OF[kind]} was called or resumed this turn"
    if kind == "LOOP" and t.get("round_started"):
        return "an implementer round was started or resumed with the evidence after the failing result"
    if kind == "LOOP" and not t["fell_short"]:
        return "no test or tester result in this turn says the purpose fell short"
    if kind == "REVIEWER" and "reviewer" in t["pending"]:
        return "a review of these changes is running"
    if kind in ("TESTER", "KNOWLEDGE-MANAGER") and t["review_open"]:
        return "the latest review asked for fixes that are not done yet; testing and documenting wait for them"
    if kind == "SETUP-MANAGER" and t["sm_ok"]:
        return "the setup-manager was called after the setup edit, or nothing in the setup was edited"
    if kind == "SETUP-MANAGER" and "reviewer" in t["pending"]:
        return "a review of the change is running; it is committed after the review"
    if kind == "SETUP-MANAGER" and t["review_open"]:
        return "the latest review asked for fixes that are not done yet; the commit comes after them"
    if ctx.hedged(reason):
        return "its own reason hedges"
    if kind in AGENT_OF and t["pending"] and not t["claims"]:  # a change still being made cannot be tested or reviewed yet
        return f"a background agent ({', '.join(t['pending'])}) is still running and the final message does not claim it is done"
    return None
