"""Stop hook (output gate). A brain checks the last assistant turn and its tool calls against the cases retrieved for
it. A clear violation -> {"decision":"block","reason":...} so the session continues and fixes it. Honors
stop_hook_active (never blocks twice in a row). The delegation check (delegate.py) runs too and both reasons come in one block. Never fails the stop: any error -> exit 0."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, verdicts  # stdlib only; brain/capture/retrieve import numpy and fastembed, so they load inside main()


def stop_limit():
    """The gate's own timeout from settings.json (one source, no copy); 180 if it cannot be read."""
    try:
        s = json.load(open(os.path.join(ctx.ROOT, "settings.json"), encoding="utf-8"))
        return next(h["timeout"] for g in s["hooks"]["Stop"] for h in g["hooks"] if "gate.py" in h["command"])
    except (OSError, ValueError, KeyError, StopIteration):
        return 180


STOP_LIMIT = stop_limit()  # no new brain call starts after STOP_LIMIT - brain.TIMEOUT seconds

PROMPT = ("Cases (lessons from earlier mistakes of this assistant):\n{cases}\n\nThe assistant's latest turn.\n"
          "Tool calls this turn:\n{tools}\n\nFinal message:\n{text}\n\nDoes this turn CLEARLY violate one of the cases "
          "(e.g. claims something works or is done with no run of a test or the app in the tool calls)? Be strict: "
          "unclear or merely possible -> OK. Reply 'OK' or 'VIOLATION <id> | <one short sentence: what is wrong and "
          "what to do now>'.")


def candidates(text, tools, exclude=()):
    """[(score, case id, path or None)]: the graph's reply step (the turn vs what-was-done nodes) when graph-recall is on, else
    the flat search. exclude = occurrence keys held out (evals only)."""
    q = ctx.chunks(text) + ctx.chunks("\n".join(tools))
    if ctx.enabled("graph-recall"):
        import graph
        return graph.at_reply(q, 6, set(exclude))
    import retrieve
    return [(s, c, None) for s, c in retrieve.search(q, 6, "emb", skip=exclude)]


def check_all(tp, text, tools):
    """Slot recall-all-lessons: one call with every lesson; [(id, why)] of each clearly broken one, or None."""
    import alllessons as al, brain
    ls = al.lessons()
    out, tok = brain.ask(al.GATE.format(lessons=al.block(ls), tools="\n".join(tools) or "(none)", text=text), tag="gate-all")
    found = al.named(out, ls, "VIOLATION")
    for cid, why in found:
        verdicts.log(tp, "lesson", "BLOCK", cid, ctx.hedged(why), tokens=tok)
    if not found:
        verdicts.log(tp, "lesson", "OK", tokens=tok)
    return found or None


def check(tp, exclude=()):
    """[(case id, why)] of every violated case, or None. exclude (evals only) keeps the embedding path, which can hold out."""
    import brain, graph, index
    text, tools = ctx.last_turn(tp)
    if not text.strip():
        ctx.log("gate: no assistant text in the last turn")
        verdicts.log(tp, "lesson", "OK", skip="no assistant text")
        return None
    if ctx.enabled("recall-all-lessons") and not exclude:
        return check_all(tp, text, tools)
    hits = [h for h in candidates(text, tools, exclude) if h[0] >= ctx.RELEVANCE_MIN]
    if not hits:
        ctx.log("gate: no case above the relevance cutoff")
        verdicts.log(tp, "lesson", "OK", skip="no case above the cutoff")
        return None
    metas = {c: index.meta(c) for _, c, _ in hits}
    block = "\n".join(graph.case_line(c, metas[c], p) for _, c, p in hits)  # a path: the matched past action and his complaint
    out, tok = brain.ask(PROMPT.format(cases=block, tools="\n".join(tools) or "(none)", text=text), tag="gate")
    if out.startswith("VIOLATION"):
        cid, _, why = [x.strip(" *`") for x in out[len("VIOLATION"):].partition("|")]
        if cid in metas:
            verdicts.log(tp, "lesson", "BLOCK", cid, ctx.hedged(why), tokens=tok)
            return [(cid, why)]
    verdicts.log(tp, "lesson", "OK", tokens=tok)
    return None


def delegation(tp):
    """The delegation gate's block reason, or None. Any error is logged and counts as no block."""
    if not ctx.enabled("delegation-gate"):
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
    try:  # first, also on the reply that follows a block: that reply is where he or the session calls the block a false alarm
        import gatecases
        gatecases.label(d.get("transcript_path", ""))
    except Exception as e:
        ctx.log(f"gate: labelling failed: {e!r}")
    tp = d.get("transcript_path", "")
    owed = None  # a `capture.py write` is still unpaid (capowed.py): blocks once, fails open
    try:
        import capowed
        owed = capowed.settle(tp, d.get("stop_hook_active"))
    except Exception as e:
        ctx.log(f"gate: capture check failed: {e!r}")
    if d.get("stop_hook_active"):
        return
    found = check(tp) or []  # both checks always run, so one block carries every reason (a block from one never hides the other)
    reasons = []
    for cid, why in found:
        if ctx.hedged(why):
            ctx.log(f"gate: violation of cases/{cid}.md dropped, its own reason hedges: {why}")
            continue
        rec = (f" Then record this occurrence, you have the context: `python -I scripts/recall/capture.py write <json file>` with "
               f"{{source: \"gate\", lesson_id: \"{cid}\", situation, did, disliked = the gate's reason above}}; an unknown part "
               "is \"(not stated)\", never a guess." if ctx.enabled("capture") else "")
        if rec:
            try:
                import capowed
                capowed.owe("gate", tp)
            except Exception as e:
                ctx.log(f"gate: capture marker failed: {e!r}")
        reasons.append(f"Output gate (cases/{cid}.md): {why} Fix this now, then finish.{rec}")
    if owed:
        reasons.append(owed)
    dr = delegation(tp)
    if dr:
        reasons.append(dr)
    verdicts.log(tp, "gate", "SENT" if reasons else "PASS", rule=str(len(reasons)))
    if reasons:
        print(json.dumps({"decision": "block", "reason": "\n".join(reasons)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        ctx.log(f"gate: failed: {e!r}")
    sys.exit(0)
