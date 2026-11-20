"""Retrieval over cases: method = bm25 | emb | hybrid (reciprocal rank fusion).
Documents of a case (one embedding each): its situation lines, wrong, right, lesson, and one short structured example
per real occurrence (cases/history/<id>.md, cleaned by clean.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import embed, index

N = 100
FIELDS = ("situation", "wrong", "right", "lesson")


def docs(history=True, fields=FIELDS, skip=()):
    """{case id: [texts]}. history=False -> the case's own fields only (the baseline of the held-out test).
    skip = occurrence keys (index.occ_key) left out."""
    out = {}
    for f in index.case_files():
        d = index.parse(f)
        cid = d.get("id") or os.path.basename(f)[:-3]
        t = []
        for k in fields:
            v = d.get(k, [])
            t += v if isinstance(v, list) else [v]
        out[cid] = [x for x in t if x] + (index.history_texts(os.path.basename(f)[:-3], skip) if history else [])
    return out


def search(query, k=3, method="hybrid", backend=embed.DEFAULT, history=True, fields=FIELDS, skip=(), cache_query=True):
    """Return [(score, id)] best first. Score scale differs per method. cache_query=False: the query's vectors are not stored."""
    if method != "emb" and not isinstance(query, str):
        query = "\n".join(query)
    if method == "bm25":
        return index.search(query, k)
    emb = sorted(embed.scores(query, docs(history, fields, skip), backend, cache_query).items(), key=lambda x: -x[1])
    if method == "emb":
        return [(s, c) for c, s in emb[:k]]
    bm = index.search(query, N)
    rrf = {}
    for lst in ([c for _, c in bm], [c for c, _ in emb]):
        for r, c in enumerate(lst):
            rrf[c] = rrf.get(c, 0) + 1 / (60 + r)
    return sorted(((s, c) for c, s in rrf.items()), reverse=True)[:k]
