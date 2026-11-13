"""Retrieval over cases: method = bm25 | emb | hybrid (reciprocal rank fusion), with or without enrichment."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import embed, index

N = 100


def docs(enriched):
    out = {}
    for f in index.case_files():
        d = index.parse(f)
        out[d.get("id") or os.path.basename(f)[:-3]] = d.get("situation", []) + [d.get("lesson", "")] + (d.get("enriched", []) if enriched else [])
    return out


def search(query, k=3, method="hybrid", enriched=True, backend=embed.DEFAULT):
    """Return [(score, id)] best first. Score scale differs per method."""
    if method != "emb" and not isinstance(query, str):
        query = "\n".join(query)
    if method == "bm25":
        return index.search(query, k, enriched)
    emb = sorted(embed.scores(query, docs(enriched), backend).items(), key=lambda x: -x[1])
    if method == "emb":
        return [(s, c) for c, s in emb[:k]]
    bm = index.search(query, N, enriched)
    rrf = {}
    for lst in ([c for _, c in bm], [c for c, _ in emb]):
        for r, c in enumerate(lst):
            rrf[c] = rrf.get(c, 0) + 1 / (60 + r)
    return sorted(((s, c) for c, s in rrf.items()), reverse=True)[:k]
