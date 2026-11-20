"""Shadow select: on each gate call, after the real all-lessons check, the embedding path ("select") runs next to it and logs which
lessons it would have sent, with no model call and no effect on the verdict, so "all" and "select" can be compared on real data.
One line per gate call in results/shadow_select.jsonl: {date, transcript, all_named: [ids], select_top: [[id, score], ...]}.
Slot `shadow-select`. Never fails the gate: any error is logged and ignored.
Usage: python -I scripts/recall/shadow.py report [--log <file>]"""
import collections, datetime, json, os, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

TOP_K = 3  # lessons "select" would send per call
MARGIN = 30  # s: shadow starts only when at least this much of ctx.BUDGET is left (the delegation check still follows the gate's own call)
MAX_RUN = 15  # s: the shadow step is given up after this long; the gate goes on without it
PATH = os.path.join(ctx.ROOT, "scripts", "recall", "results", "shadow_select.jsonl")


def path():
    return os.environ.get("RECALL_SHADOW_LOG") or PATH  # the tests point it at a temp file


def top(text, tools):
    """[[lesson id, cosine]] best first: the embedding search over the lessons and their active situations, above RELEVANCE_MIN."""
    import retrieve
    q = ctx.chunks(text) + ctx.chunks("\n".join(tools))
    return [[c, round(s, 3)] for s, c in retrieve.search(q, TOP_K, "emb", cache_query=False) if s >= ctx.RELEVANCE_MIN]


def _write(tp, text, tools, named):
    row = {"date": datetime.date.today().isoformat(), "transcript": os.path.basename(tp or ""), "all_named": list(named),
           "select_top": top(text, tools)}
    with open(path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def record(tp, text, tools, named):
    """Append the shadow line of this gate call (named = ids the real check named). Skipped when less than MARGIN s of the time
    budget is left; the step runs in a thread that is given up after MAX_RUN s (a hung model never holds the gate)."""
    try:
        if not ctx.enabled("shadow-select"):
            return
        if time.monotonic() - ctx.T0 > ctx.BUDGET - MARGIN:
            ctx.log("shadow: skipped, too little of the time budget left")
            return
        err = []
        def work():
            try:
                _write(tp, text, tools, named)
            except Exception as e:
                err.append(e)
        t = threading.Thread(target=work, daemon=True)
        t.start()
        t.join(MAX_RUN)
        if t.is_alive():
            ctx.log(f"shadow: given up after {MAX_RUN}s")
        elif err:
            raise err[0]
    except Exception as e:
        ctx.log(f"shadow: not written: {e!r}")


def report(rows):
    """Per lesson named by "all": calls it was named, and how often select had it in its top-k; and the overall hit rate."""
    per = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        got = {c for c, _ in r["select_top"]}
        for c in r["all_named"]:
            per[c][0] += 1
            per[c][1] += c in got
    n, hit = sum(v[0] for v in per.values()), sum(v[1] for v in per.values())
    lines = [f"gate calls {len(rows)}; named by all {n}; select (top {TOP_K}, cosine >= {ctx.RELEVANCE_MIN}) had them: {hit}"
             + (f" = {hit / n:.0%}" if n else ""),
             f"calls where all named nothing but select sent something: {sum(not r['all_named'] and bool(r['select_top']) for r in rows)}"]
    lines += [f"  {c:40} named {v[0]:3d}  in select top {v[1]:3d} ({v[1] / v[0]:.0%})" for c, v in sorted(per.items(), key=lambda kv: -kv[1][0])]
    return "\n".join(lines)


def read(log):
    try:
        return [json.loads(l) for l in open(log, encoding="utf-8") if l.strip()]
    except OSError:
        return []


if __name__ == "__main__" and sys.argv[1:2] == ["report"]:
    a = sys.argv[2:]
    print(report(read(a[a.index("--log") + 1] if "--log" in a else path())))
