"""Recall eval on the 40 labelled queries: method x enrichment. Per row the threshold is swept and the best is
kept (max recall@3 with <=1 false positive on the negatives; ties -> fewer FP, then higher threshold).
Threshold is picked on the same 40 queries, so the numbers are optimistic."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import math
import capture, ctx, embed, retrieve

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


def hist(vals, lo=0.5, hi=0.9, step=0.05):
    return "  ".join(f"{lo + i * step:.2f}:{sum(lo + i * step <= v < lo + (i + 1) * step for v in vals)}"
                     for i in range(round((hi - lo) / step)))


def cutoffs(rows):
    """Score distributions for the method the hooks use (emb, fastembed, enriched) and the two cutoffs they need.
    RELEVANCE_MIN: the lowest 0.01 step where at most 1 unrelated query passes (~5%); the strict second brain call
    is the real filter, this only saves it on clearly unrelated text.
    SAME (capture.py): same-case paraphrase scores vs best other-case / unrelated scores."""
    own, other, neg = [], [], []
    for r in rows:
        sc = embed.scores(r["q"], retrieve.docs(True), "fastembed")
        if r["case"]:
            own.append(sc[r["case"]])
            other.append(max(v for c, v in sc.items() if c != r["case"]))
        else:
            neg.append(max(sc.values()))
    rel = next(t / 100 for t in range(50, 100) if sum(v >= t / 100 for v in neg) <= 1)
    print(f"\nscore distributions (emb, fastembed, enriched), bins of 0.05 from 0.50:")
    print(f"  positives (score of its own case, n={len(own)}): min {min(own):.3f} median {sorted(own)[len(own) // 2]:.3f}  {hist(own)}")
    print(f"  negatives (top score of any case, n={len(neg)}): max {max(neg):.3f} median {sorted(neg)[len(neg) // 2]:.3f}  {hist(neg)}")
    print(f"  chosen RELEVANCE_MIN = {rel:.2f}: recall@1-case {sum(v >= rel for v in own)}/{len(own)}, "
          f"false positives {sum(v >= rel for v in neg)}/{len(neg)}  (ctx.RELEVANCE_MIN is {ctx.RELEVANCE_MIN})")
    diff = other + neg
    print(f"  SAME: same case min {min(own):.3f}, different case/unrelated max {max(diff):.3f}, "
          f"same cases below the max different: {sum(v <= max(diff) for v in own)}/{len(own)}")
    print(f"  SAME floor (0 wrong merges) = {math.ceil((max(diff) + 0.001) * 100) / 100:.2f}; capture.SAME = {capture.SAME} keeps a margin")
    for t in (0.70, 0.75, 0.80, 0.85):
        print(f"    SAME={t:.2f}: merges {sum(v >= t for v in own)}/{len(own)} paraphrases, wrongly merges {sum(v >= t for v in diff)}/{len(diff)} different")


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
    cutoffs(rows)


if __name__ == "__main__":
    main()
