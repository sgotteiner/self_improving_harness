"""Stop hook (output gate). A brain checks the last assistant turn and its tool calls against the cases retrieved for
it. A clear violation -> {"decision":"block","reason":...} so the session continues and fixes it. Honors
stop_hook_active (never blocks twice in a row). The delegation check (delegate.py) runs too and both reasons come in one block. Never fails the stop: any error -> exit 0."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx  # stdlib only; brain/capture/retrieve import numpy and fastembed, so they load inside main()
STOP_LIMIT = 180  # the Stop timeout in settings.json; no new brain call starts after STOP_LIMIT - brain.TIMEOUT seconds

PROMPT = ("Cases (lessons from earlier mistakes of this assistant):\n{cases}\n\nThe assistant's latest turn.\n"
          "Tool calls this turn:\n{tools}\n\nFinal message:\n{text}\n\nDoes this turn CLEARLY violate one of the cases "
          "(e.g. claims something works or is done with no run of a test or the app in the tool calls)? Be strict: "
          "unclear or merely possible -> OK. Reply 'OK' or 'VIOLATION <id> | <one short sentence: what is wrong and "
          "what to do now>'.")


def check(tp):
    import brain, index, retrieve
    text, tools = ctx.last_turn(tp)
    if not text.strip():
        ctx.log("gate: no assistant text in the last turn")
        return None
    hits = [(s, c) for s, c in retrieve.search(ctx.chunks(text) + ctx.chunks("\n".join(tools)), 6, "emb")
            if s >= ctx.RELEVANCE_MIN]
    if not hits:
        ctx.log("gate: no case above the relevance cutoff")
        return None
    metas = {c: index.meta(c) for _, c in hits}
    block = "\n".join(f"- {c}: situation: {m[1]} Lesson: {m[2]} Right: {m[3]}" for c, m in metas.items())
    out, _ = brain.ask(PROMPT.format(cases=block, tools="\n".join(tools) or "(none)", text=text), tag="gate")
    if out.startswith("VIOLATION"):
        cid, _, why = [x.strip(" *`") for x in out[len("VIOLATION"):].partition("|")]
        if cid in metas:
            return cid, why
    return None


def delegation(tp):
    """The delegation gate's block reason, or None. Any error is logged and counts as no block."""
    if not ctx.enabled("delegation-hook"):
        return None
    try:
        import delegate
        d, _ = delegate.output_step(tp)
        return d[1] if d else None
    except Exception as e:
        ctx.log(f"gate: delegation failed: {e!r}")
        return None


def main():
    if ctx.skip_env("RECALL_GATE") or not ctx.enabled("output-gate"):
        return
    import brain
    ctx.BUDGET = STOP_LIMIT - brain.TIMEOUT
    d = json.load(sys.stdin)
    if d.get("stop_hook_active"):
        return
    tp = d.get("transcript_path", "")
    r = check(tp)  # both checks always run, so one block carries every reason (a block from one never hides the other)
    reasons = []
    if r and ctx.hedged(r[1]):
        ctx.log(f"gate: violation of cases/{r[0]}.md dropped, its own reason hedges: {r[1]}")
        r = None
    if r:
        cid, why = r
        if ctx.enabled("capture"):
            try:
                import capture
                capture.from_gate(cid, why, tp)
            except Exception as e:
                ctx.log(f"gate: capture failed: {e!r}")
        reasons.append(f"Output gate (cases/{cid}.md): {why} Fix this now, then finish.")
    dr = delegation(tp)
    if dr:
        reasons.append(dr)
    if reasons:
        print(json.dumps({"decision": "block", "reason": "\n".join(reasons)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        ctx.log(f"gate: failed: {e!r}")
    sys.exit(0)
