"""Evals only (eval_mechanism.py, part c): does capture attach a mistake that is already known to its lesson (right one, wrong
one) or draft a duplicate? Each real correction is replayed through the real detect + draft brain calls (cached, concurrent),
as if new with its own path held out; each pending draft is compared with everything but itself."""
import os
from concurrent.futures import ThreadPoolExecutor
import brain, capture, ctx, graph, index, mechbrain, pending

MODES = ("all", "single", "agree")  # graph.ATTACH


def _replay(o):
    prev, tools = ctx.last_turn(o["tp"])
    det, _ = brain.ask(capture.DETECT.format(prev=prev, tools="; ".join(tools) or "none", rej="", prompt=o["text"]), tag="eval-detect")
    why = det.partition("|")[2].strip() or "the assistant's mistake"
    d = pending.json_of(brain.ask(capture.DRAFT.format(why=why, prev=prev, prompt=o["text"]), tag="eval-draft")[0])
    return (o, d, why) if d and d.get("situation") else (o, None, why)


def corrections(occ):
    """[(occurrence, draft or None, why)] for each correction occurrence whose turn is available."""
    ctx.BUDGET = 10 ** 9
    with ThreadPoolExecutor(16) as pool:
        return list(pool.map(_replay, [o for o in occ if o["source"] == "correction" and o["tp"]]))


def attach(reps, lessons):
    """{mode: (own, wrong, none, N)}: what the graph attaches a replayed correction to: only its own lessons / any other lesson /
    nothing (a new draft). 'off' is the flat single-best case."""
    out = {}
    for mode in ("off",) + MODES:
        r = []
        for o, d, why in reps:
            if not d:
                continue
            ex = {o["key"]}
            if mode == "off":
                mechbrain.graph_switch(False)
                hit = capture.matches(d, why, ex)
            else:
                graph.ATTACH = mode
                hit = capture.graph_matches(d, why, ex)
            r.append("none" if not hit else "own" if set(hit) <= set(lessons[o["key"]]) else "wrong")
        out[mode] = (r.count("own"), r.count("wrong"), r.count("none"), len(r))
    graph.ATTACH = "all"
    return out


def drafts():
    """{mode: how many of the pending drafts are attached to some other lesson (the rest stay new drafts)}, N."""
    pd, ds = os.path.join(index.CASES, "_pending"), []
    for f in sorted(os.listdir(pd)):
        if f.endswith(".md") and f != "README.md":
            ds.append((f[:-3], index.parse(os.path.join(pd, f))))
    out = {}
    for mode in ("off",) + MODES:
        n = 0
        for slug, d in ds:
            ex = {"_pending/" + slug}
            if mode == "off":
                mechbrain.graph_switch(False)
                n += bool(capture.matches(d, d.get("his_words", ""), ex))
            else:
                graph.ATTACH = mode
                n += bool(capture.graph_matches(d, d.get("his_words", ""), ex))
        out[mode] = n
    graph.ATTACH = "all"
    return out, len(ds)
