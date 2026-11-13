"""Recall eval on the 40 labelled queries: method x enrichment. Per row the threshold is swept and the best is
kept (max recall@3 with <=1 false positive on the negatives; ties -> fewer FP, then higher threshold).
Threshold is picked on the same 40 queries, so the numbers are optimistic."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import embed, retrieve

CONFIGS = [("bm25", "-"), ("emb", "model2vec"), ("emb", "fastembed"), ("hybrid", "model2vec"), ("hybrid", "fastembed")]


def run(method, backend, enriched, rows):
    res = [(r, retrieve.search(r["q"], 3, method, enriched, backend if backend != "-" else embed.DEFAULT)) for r in rows]
    pos, neg = [x for x in res if x[0]["case"]], [x for x in res if not x[0]["case"]]
    best = None
    for t in sorted({s for _, hs in res for s, _ in hs} | {0.0}):
        hit = sum(any(s >= t and c == r["case"] for s, c in hs) for r, hs in pos)
        fp = sum(any(s >= t for s, c in hs) for r, hs in neg)
        if fp <= 1 and (best is None or (hit, -fp, t) > (best[0], -best[1], best[2])):
            best = (hit, fp, t)
    best = best or (0, len(neg), float('inf'))  # no threshold keeps false positives <=1
    return best, len(pos), len(neg), res


def main():
    rows = [json.loads(l) for l in open(os.path.join(embed.HERE, "eval_set.jsonl"), encoding="utf-8") if l.strip()]
    print(f"{'method':8} {'backend':10} {'enriched':8} {'recall@3':12} {'false pos':9} threshold")
    out = []
    for method, backend in CONFIGS:
        for enr in (False, True):
            (hit, fp, t), npos, nneg, res = run(method, backend, enr, rows)
            out.append((hit, -fp, method, backend, enr))
            print(f"{method:8} {backend:10} {str(enr):8} {hit:2d}/{npos} {hit/npos:5.0%}   {fp}/{nneg}       {t:.4f}")
            if "--misses" in sys.argv:
                for r, hs in res:
                    if r["case"] and not any(s >= t and c == r["case"] for s, c in hs):
                        print("     MISS", r["case"], "|", r["q"][:60], "|", [(round(s, 2), c[:12]) for s, c in hs][:1])
    b = max(out)
    print("best:", b[2], b[3], "enriched" if b[4] else "plain", f"recall {b[0]}")


if __name__ == "__main__":
    main()
