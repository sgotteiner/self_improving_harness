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


def need(prompt, names):
    miss = [n for n in names if "{" + n + "}" not in prompt]
    if miss:
        raise ValueError("placeholder(s) missing: " + ", ".join(miss))


def keys(lines, want):
    miss = [k for k in want if k not in lines]
    if miss:
        raise ValueError("bullet(s) missing: " + ", ".join(miss))


def check_sources(rules, prompt, lines, line_keys, block_keys):
    """[problem] when CLAUDE.md or the draft no longer parse the way the hooks read them (a renamed heading must fail loudly, not
    silently turn the delegation off). Run by `capture.py check` through delegate.check_sources."""
    out = []
    for label, fn in (("CLAUDE.md section 'The core'", rules),
                      ("draft prompt 'Input step'", lambda: need(prompt("Input step"), ("prev", "prompt"))),
                      ("draft prompt 'Done question'", lambda: prompt("Done question")),
                      ("draft prompt 'Output step'", lambda: need(prompt("Output step"), ("rules", "human", "tools", "text", "facts", "max_rounds"))),
                      ("draft 'Instruction lines attached'", lambda: keys(lines("Instruction lines attached"), line_keys)),
                      ("draft 'Block reasons'", lambda: keys(lines("Block reasons"), block_keys))):
        try:
            fn()
        except (ValueError, OSError) as e:
            out.append(f"{label}: {e}")
    return out


def reason(tp):
    """The delegation gate's block reason (slot delegation-gate), or None. Any error is logged and counts as no block."""
    if not ctx.enabled("delegation-gate"):
        return None
    try:
        import delegate
        d, _ = delegate.output_step(tp)
        return d[1] if d else None
    except Exception as e:
        ctx.log(f"gate: delegation failed: {e!r}")
        return None
