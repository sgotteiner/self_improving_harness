"""Free selection of the graph's lesson scoring (no model call): every variant against flat and flat-split, held-out, each with
its OWN cutoff from the unrelated queries. Usage: python -I scripts/recall/eval_variants.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, graph, index, mechretr, mechturns

# (name, method, graph.VARIANT, graph.REPLY_KINDS)
METHODS = [("flat(today)", "flat", "best", None), ("flat-split", "split", "best", None)] + [
    (n, "graph", v, rk) for n, v, rk in (("g:best", "best", None), ("g:path", "path", None), ("g:norm2", "norm2", None), ("g:norm4", "norm4", None),
     ("g:best+lesson", "best", ("action", "path", "lesson")), ("g:best+sit", "best", ("action", "path", "situation")),
     ("g:norm2+lesson", "norm2", ("action", "path", "lesson")))]


def run(turns=None, clean=(), methods=METHODS):
    """{name: dict of measures}; one row printed per method."""
    qs, out = mechretr.queries(turns, clean), {}
    biased = max({c for q in qs if q["lessons"] for c in q["lessons"]}, key=lambda c: len(index.history_records(c)))
    for name, m, var, rk in methods:
        graph.VARIANT, graph.REPLY_KINDS = var, rk or ("action", "path")
        res = [mechretr.top(m, q["step"], q["q"], q["skip"]) for q in qs]
        r = {}
        for step in ("message", "reply"):
            t = r["thr_" + step] = mechretr.threshold(res, qs, step)
            for src in ("labelled", "held-out"):
                ids = [i for i, q in enumerate(qs) if q["step"] == step and q["src"] == src and q["lessons"]]
                if ids:
                    r[src[:3] + "_" + step] = (sum(res[i][0][1] in qs[i]["lessons"] for i in ids),
                                              sum(any(c in qs[i]["lessons"] for _, c in res[i]) for i in ids),
                                              sum(any(c in qs[i]["lessons"] and s >= t for s, c in res[i]) for i in ids), len(ids))
            ids = [i for i, q in enumerate(qs) if q["step"] == step and q["lessons"] and biased not in q["lessons"]]
            r["bias_" + step] = (sum(any(c == biased and s >= t for s, c in res[i]) for i in ids), len(ids))
            r["fp_" + step] = sum(any(s >= t for s, _ in res[i]) for i, q in enumerate(qs) if q["lessons"] is None and q["step"] == step)
        out[name] = r
    graph.VARIANT, graph.REPLY_KINDS = "best", ("action", "path")
    return out, biased


def show(out, biased):
    f = lambda x: "-" if x is None else "/".join(map(str, x[:3])) + f" of {x[3]}"
    print(f"retrieval, held-out twins excluded, own cutoff per method. recall = @1/@3/@3 above cutoff; bias = {biased} in the top 3 above cutoff on other cases' queries")
    print(f"{'method':16} {'cut m/r':9} {'lab msg':11} {'held msg':11} {'held reply':12} {'bias msg':9} {'bias reply':10} fp m/r")
    for n, r in out.items():
        print(f"{n:16} {r['thr_message']:.2f}/{r['thr_reply']:.2f} {f(r.get('lab_message')):11} {f(r.get('hel_message')):11} "
              f"{f(r.get('hel_reply')):12} {'%d/%d' % r['bias_message']:9} {'%d/%d' % r['bias_reply']:10} {r['fp_message']}/{r['fp_reply']}")


if __name__ == "__main__":
    occ = mechturns.occurrence_turns()
    turns = {o["key"]: o["tp"] for o in occ if o["tp"]}
    ms = [m for m in METHODS if not sys.argv[1:] or m[0] in sys.argv[1:]]  # names on the command line: only those
    show(*run(turns, [c["tp"] for c in mechturns.clean_turns(occ)], ms))
