"""Evals only: the free retrieval measures (no model call) of eval_mechanism.py / eval_variants.py. Queries: the labelled set
(message step), every real occurrence held out (message step: its situation; reply step: its rebuilt assistant turn the way the
gate queries, else its 'assistant did'), and unrelated texts (labelled unrelated messages; clean turns for the reply step).
Held out = the occurrence's own path AND its twins (the same real event recorded on another lesson, cleaned separately)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, embed, graph, index, retrieve

K = 3


def split_docs(skip):
    """Fair flat baseline: the case's own fields + every occurrence part of EVERY case as its own text."""
    d = retrieve.docs(False)
    for cid in d:
        d[cid] = d[cid] + [r[k] for r in index.history_records(cid) if index.occ_key(r) not in skip for k in index.PARTS[:3] if r.get(k)]
    return d


def twins(occs):
    """{key: {keys of the same real event}}: same date and source, situation at or above SAME."""
    v = embed.encode([" ".join(p["sit"]) for p in occs])
    return {p["key"]: {q["key"] for j, q in enumerate(occs) if q["key"][:2] == p["key"][:2] and float(v[i] @ v[j]) >= ctx.SAME}
            for i, p in enumerate(occs)}


def queries(turns=None, clean=()):
    """turns = {occurrence key: rebuilt turn path}. -> [{step, q, lessons (None = unrelated), skip, group, src}]."""
    out = []
    for l in open(os.path.join(embed.HERE, "eval_set.jsonl"), encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            out.append(dict(step="message", q=r["q"], lessons={r["case"]} if r["case"] else None, skip=set(), group=r["case"] or "(unrelated)", src="labelled"))
    occs = graph.occurrences()
    tw = twins(occs)
    for p in occs:
        t = (turns or {}).get(p["key"])
        qr = ctx.chunks(ctx.last_turn(t)[0]) + ctx.chunks("\n".join(ctx.last_turn(t)[1])) if t else p["did"]
        for step, q in (("message", " ".join(p["sit"])), ("reply", qr)):
            out.append(dict(step=step, q=q, lessons=set(p["lessons"]), skip=tw[p["key"]], group=p["lessons"][0], src="held-out"))
    for tp in clean:
        t, tools = ctx.last_turn(tp)
        out.append(dict(step="reply", q=ctx.chunks(t) + ctx.chunks("\n".join(tools)), lessons=None, skip=set(), group="(clean turn)", src="labelled"))
    return out


def top(method, step, q, skip, k=K):
    """[(score, lesson id)] best first. method: flat | split | graph (graph.VARIANT / REPLY_KINDS as set by the caller)."""
    if method == "flat":
        return retrieve.search(q, k, "emb", skip=skip)
    if method == "split":
        return sorted(((s, c) for c, s in embed.scores(q, split_docs(skip)).items()), reverse=True)[:k]
    return [(s, c) for s, c, _ in (graph.at_message if step == "message" else graph.at_reply)(q, k, set(skip))]


def threshold(res, qs, step, allowed=1):
    """Own cutoff of a method: the lowest 0.01 step where at most `allowed` unrelated queries have a top-3 score at or above it
    (the rule of ctx.RELEVANCE_MIN). res[i] = top() of query i."""
    neg = [res[i] for i, q in enumerate(qs) if q["lessons"] is None and q["step"] == step]
    for t in range(40, 100):
        if sum(any(s >= t / 100 for s, _ in r) for r in neg) <= allowed:
            return t / 100
    return 1.0
