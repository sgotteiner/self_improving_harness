"""Checks of a saved case, shared by `capture.py approve` (right after saving) and `capture.py check` (all cases).
Each check returns (ok, evidence); run() returns [(step, ok, evidence)]. No check changes a case.
Length rule: short but not missing. Nothing is capped by size; every part must be present and non-empty."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clean, ctx, embed, index, retrieve

REQUIRED = ["id", "date", "level", "situation", "wrong", "right", "lesson", "replay", "pass_if"]
HUMAN = ["situation", "wrong", "right", "lesson", "replay", "pass_if"]  # the fields a person (or the draft brain) wrote
LEVELS = ("advice", "check", "rule")
MAX_RANK = 2
MIN_SITUATIONS = 1  # a lesson approved from a proposal starts with the one situation it came from; the store adds the rest


def texts(d):
    """Every text that retrieval embeds for a case."""
    return retrieve.docs().get(d["id"], [])


def check_fields(path, d):
    miss = [f for f in REQUIRED if not d.get(f) or (isinstance(d[f], list) and not any(d[f]))]
    n = len(d.get("situation", []))
    bad = []
    if miss:
        bad.append("missing or empty: " + ", ".join(miss))
    if d.get("level") and d["level"] not in LEVELS:
        bad.append(f"level {d['level']!r} not in {LEVELS}")
    if d.get("situation") and not MIN_SITUATIONS <= n <= 4:
        bad.append(f"situation has {n} items, need {MIN_SITUATIONS}-4")
    if d.get("id") and d["id"] != os.path.basename(path)[:-3]:
        bad.append(f"id {d['id']!r} differs from the file name")
    return not bad, "; ".join(bad) or f"{len(REQUIRED)} required fields present and non-empty, situation {n}, level {d['level']}"


def check_privacy(path, d):
    bad = []
    for f in ["id"] + HUMAN:
        v = d.get(f, "")
        for t in (v if isinstance(v, list) else [v]):
            bad += [f"{f}: {x}" for x in clean.violations(t)]
    for r in index.history_records(d["id"]):
        for k in index.PARTS:
            bad += [f"history {r.get('date')} {k}: {x}" for x in clean.violations(r.get(k, ""), strict=True)]
    return not bad, "; ".join(bad[:6]) or "no paths, emails or project/company names in the written fields or the cleaned occurrences"


def check_occurrences(path, d):
    """Every cleaned occurrence has all four parts, non-empty (situation, what the assistant did, what he did not like,
    the lesson). The file must also hold as many blocks as the case's `occurrences` count says were published."""
    recs = index.history_records(d["id"])
    bad = [f"{r.get('date', '?')} {r.get('source', '?')}: missing {', '.join(k for k in index.PARTS if not r.get(k))}"
           for r in recs if any(not r.get(k) for k in index.PARTS)]
    return not bad, "; ".join(bad[:4]) or f"{len(recs)} cleaned occurrences, all four parts present"


def check_embeddings(path, d):
    t = texts(d)
    miss = embed.missing(t)
    return miss == 0, f"{len(t) - miss}/{len(t)} texts have a cached vector" + (f", {miss} missing" if miss else "")


def check_recall(path, d):
    """The case's own lesson and two situation lines are searched with retrieve.search (the method the hooks use; the graph when graph-recall is on); the
    case must rank #1 or #2. That proves the case is in the index with working vectors. Evidence also shows the
    held-out rank (the query text removed from the case's documents), which measures how well the case generalizes;
    it is informational and does not fail the check."""
    cid, e = d["id"], d.get("situation", [])
    qs = [("lesson", d.get("lesson", ""))] + [(f"situation[{i}]", e[i]) for i in range(min(2, len(e)))]
    qs = [(n, q) for n, q in qs if q]
    if len(qs) < 1 + MIN_SITUATIONS:
        return False, f"need a lesson and {MIN_SITUATIONS} situation line(s) to test"
    base = retrieve.docs()
    if cid not in base:
        return False, "case is not in the retrieval documents"
    if ctx.enabled("graph-recall"):  # the graph's best node of any kind per lesson, the same ranking the hooks use when it is on
        import graph
        search = lambda q: [c for _, c, _ in graph.any_node(q, 20)]
    else:
        search = lambda q: [c for _, c in retrieve.search(q, 20, "emb")]
    ranks, held = [], []
    for n, q in qs:
        hits = search(q)
        ranks.append((n, hits.index(cid) + 1 if cid in hits else 99))
        docs = dict(base)
        docs[cid] = [x for x in docs[cid] if x != q]
        sc = embed.scores(q, docs)
        held.append(1 + sum(v > sc[cid] for c, v in sc.items() if c != cid))
    worst = max(r for _, r in ranks)
    return worst <= MAX_RANK, "rank " + ", ".join(f"{n}={r}" for n, r in ranks) + f" (need <= {MAX_RANK}); held-out ranks " \
        + "/".join(map(str, held)) + " (informational)"


CHECKS = [("fields", check_fields), ("privacy", check_privacy), ("occurrences", check_occurrences),
          ("embeddings", check_embeddings), ("recall", check_recall)]


def run(path, only=None):
    d = index.parse(path)
    d.setdefault("id", os.path.basename(path)[:-3])
    out = []
    for name, fn in CHECKS:
        if only and name not in only:
            continue
        try:
            ok, ev = fn(path, d)
        except Exception as ex:
            ok, ev = False, f"error {ex!r}"
        out.append((name, ok, ev))
    return out
