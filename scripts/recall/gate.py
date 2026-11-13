"""Stop hook (output gate). A brain checks the last assistant turn and its tool calls against the cases retrieved for
it. A clear violation -> {"decision":"block","reason":...} so the session continues and fixes it. Honors
stop_hook_active (never blocks twice in a row). Never fails the stop: any error -> exit 0."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx  # stdlib only; brain/capture/retrieve import numpy and fastembed, so they load inside main()

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
    hits = [(s, c) for s, c in retrieve.search(ctx.chunks(text) + ctx.chunks("\n".join(tools)), 6, "emb", True)
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


def main():
    if ctx.skip_env("RECALL_GATE") or not ctx.enabled("output-gate"):
        return
    d = json.load(sys.stdin)
    if d.get("stop_hook_active"):
        return
    tp = d.get("transcript_path", "")
    r = check(tp)
    if not r:
        return
    cid, why = r
    if ctx.enabled("capture"):
        try:
            import capture
            capture.from_gate(cid, why, tp)
        except Exception as e:
            ctx.log(f"gate: capture failed: {e!r}")
    print(json.dumps({"decision": "block", "reason": f"Output gate (cases/{cid}.md): {why} Fix this now, then finish."}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        ctx.log(f"gate: failed: {e!r}")
    sys.exit(0)
