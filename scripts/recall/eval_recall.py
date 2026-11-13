"""Recall eval: recall@3 on labelled paraphrases, false positives on negatives, per BM25 threshold."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import index

THRESHOLDS = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0]


def run():
    rows = [json.loads(l) for l in open(os.path.join(index.HERE, "eval_set.jsonl"), encoding="utf-8") if l.strip()]
    res = [(r, index.search(r["q"], 3)) for r in rows]
    pos = [x for x in res if x[0]["case"]]
    neg = [x for x in res if not x[0]["case"]]
    table = []
    for t in THRESHOLDS:
        hit = sum(any(s >= t and c == r["case"] for s, c in hs) for r, hs in pos)
        fp = sum(any(s >= t for s, c in hs) for r, hs in neg)
        table.append((t, hit, len(pos), fp, len(neg)))
    return res, table


def choose(table):
    ok = [x for x in table if x[3] <= 1]
    return max(ok, key=lambda x: (x[1], x[0]))[0]  # max recall; ties -> higher threshold


if __name__ == "__main__":
    res, table = run()
    print("threshold  recall@3      false positives")
    for t, h, n, fp, nn in table:
        print(f"{t:8.1f}   {h:2d}/{n} {h/n:5.0%}     {fp}/{nn}")
    print("chosen threshold:", choose(table))
    print("\nmisses at threshold 0 (top-3 lacks the label) and negative top scores:")
    for r, hs in res:
        if r["case"] and not any(c == r["case"] for s, c in hs):
            print("  MISS", r["case"], "|", r["q"], "|", [(round(s, 2), c) for s, c in hs])
        if not r["case"]:
            print("  NEG ", r["q"], "|", [(round(s, 2), c) for s, c in hs][:1])
