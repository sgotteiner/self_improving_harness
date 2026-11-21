"""Interventions of a feature trace: how often he had to step in, the number that shows whether the setup is learning. N = his
`correction` events; M = gate catches (situation events whose sids the situations store gives the source `gate`); K = traces that
started `from` this one. Used by tracing.render() and by `python -I scripts/recall/tracing.py interventions [project]`. Fails open."""
import glob, os

import ctx

GATE = "gate"  # the situations source of a catch by the gate (situations.SOURCES)
CORRECTION = "correction"


def counts(r, rows=()):
    """(N corrections, M gate catches, K child traces) of trace r; `rows` = the project's traces (children are found there)."""
    try:
        n = sum(1 for e in r["events"] if e["type"] == CORRECTION)
        k = sum(1 for x in rows if (x.get("from") or {}).get("tid") == r["tid"])
        sids = {s for e in r["events"] if e["type"] != CORRECTION for s in e.get("sids", [])}
        gate = set()
        if sids:
            import situations
            gate = {x["sid"] for x in situations.read() if x["sid"] in sids and x.get("source") == GATE}
        return n, len(gate), k
    except Exception as e:
        ctx.log(f"tracecount: failed: {e!r}")
        return 0, 0, 0


def _count(x, one, many):
    return f"{x} {one if x == 1 else many}" if x else ""


def line(n, m, k):
    """'Interventions: ...' with the zero parts left out; '' when all are zero."""
    parts = [p for p in (_count(n, "correction", "corrections"), _count(m, "gate catch", "gate catches"),
                         _count(k, "feature started from it", "features started from it")) if p]
    return "Interventions: " + ", ".join(parts) if parts else ""  # overlapping counts (a child trace may come from a correction), not a sum


def report(proj=""):
    """One line per closed trace (oldest first): tid, closed date, title, N, M, K."""
    import tracing
    projs = [proj] if proj else sorted(os.path.basename(f)[:-6] for f in glob.glob(os.path.join(tracing.DIR, "*.jsonl")))
    out = []
    for p in projs:
        rows = tracing.read(p)
        out += [(r["closed"], p, r, counts(r, rows)) for r in rows if r.get("closed")]
    return "\n".join(f"{p}/{r['tid']}\t{c}\t{r['title']}\tN={n}\tM={m}\tK={k}" for c, p, r, (n, m, k) in sorted(out, key=lambda t: t[:2]))
