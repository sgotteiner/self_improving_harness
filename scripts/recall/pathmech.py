"""The owner's path mechanism tried as he described it (offline, no live hook change). Usage: python -I scripts/recall/pathmech.py
Cases are paths; their sections are nodes (situation, what you did, what he did not like, lesson).
Message stage: the live situation (the template: Working on / Just done / State / He asked) vs SITUATION nodes by embedding.
Reply stage: no embedding; ONE brain call compares the turn's actions with the candidates' did + his complaint (NONE or path id | why).
Stored situations were written by the agent from the transcripts, the live one by the brain (variant A; B dropped: not free).
Measure: held-out (the query's own path removed) past mistake turns blocked, and false blocks on clean turns, vs today's gate."""
import os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mechcatch  # first: it points the verdict log at a temp file
import brain, ctx, index,mechbrain, mechturns, pathparts as pp

os.environ["RECALL_BRAIN_BACKEND"] = "gemini"  # every brain call of this eval (renders, judge, today's gate) goes direct to the API
mechbrain.install()
ctx.BUDGET = 10 ** 9
cut = lambda s, n=170: " ".join(str(s).split())[:n] + ("..." if len(" ".join(str(s).split())) > n else "")

SPEC = """SPEC CHECK (query text -> what it is compared with)
 message stage: query = the live situation in the template, written by the brain (Haiku); compared by embedding with the SITUATION
                nodes only (written by the agent from transcripts; the held-out path removed). Top %d above %.2f = candidate paths.
 reply stage:   NO embedding. ONE brain call per turn: the turn's tool calls + final message vs the candidates' did + his complaint
                (+ lesson); answer NONE or '<path id> | <what is repeated>'. A hit = block."""


def table(head, rows):
    w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
    for r in [head] + rows:
        print("  " + "  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))


def trace(title, i, n, paths, clean, live, items, cands, by, out):
    who = f"path {paths[i]['occ']}, lesson {paths[i]['lesson']}" if i < n else f"clean turn {clean[i - n]['name']}"
    print(f"\nTRACED EXAMPLE {title} ({who})\n  live situation (brain): {cut(live[i])}\n  turn: {cut(items[i][0])}\n"
          f"  tools: {cut(' | '.join(items[i][1]), 300)}")
    for s, o in cands[i]:
        print(f"  candidate path {o} (situation {s:.2f}) lesson {by[o]['lesson']}\n    did: {cut(by[o]['did'])}\n"
              f"    he disliked: {cut(by[o]['complaint'])}")
    print(f"  brain answer: {cut(out[i][1], 300)}")


def main():
    t0 = time.time()
    print(SPEC % (pp.N, pp.CUT))
    paths = pp.load()
    by = {p["occ"]: p for p in paths}
    clean = [dict(name=c["name"], tp=c["tp"], **dict(zip(("tt", "tp_msg"), pp.turn_of(c["tp"]))))
             for c in mechturns.clean_turns(None)]
    keys = {(o["cid"], o["text"]): o["key"] for o in mechturns.occurrence_turns()}  # the gate's held-out keys
    turns = [dict(tp=p["tp"], key=keys.get((p["lesson"], p["raw"]))) for p in paths] + [dict(tp=c["tp"]) for c in clean]
    base = {}
    with ThreadPoolExecutor(32) as ex:
        live = list(ex.map(pp.render, [p["tp_msg"] for p in paths] + [c["tp_msg"] for c in clean]))
    lessons = {os.path.basename(f)[:-3]: index.meta(os.path.basename(f)[:-3])[2] for f in index.case_files()}
    g, _ = pp.nodes(paths, lessons)
    sit = {o: v["situation"] for o, v in g.items()}
    items = [(p["text"], p["tools"], p["occ"]) for p in paths] + [(*c["tt"], None) for c in clean]
    cands = [pp.at_message(l, sit, it[2]) for l, it in zip(live, items)]
    th = threading.Thread(target=lambda: base.update(r=mechcatch.run(turns, None)))  # today's gate, parallel with the judging
    th.start()
    with ThreadPoolExecutor(32) as ex:
        out = list(ex.map(lambda x: pp.judge(x[0][0], x[0][1], x[1], by), zip(items, cands)))
    th.join()
    dec = [o[0] for o in out]
    ok = lambda x: x is not None and x != "!error"
    n = len(paths)
    res = dict(off=base["r"], llm=dec)
    print("\nMEASURE (held-out; mistake turns blocked | false blocks on clean turns)")
    table(["lesson", "turns"] + list(res), [[les, sum(p["lesson"] == les for p in paths)] + [
        sum(ok(r[i]) for i, p in enumerate(paths) if p["lesson"] == les) for r in res.values()] for les in sorted({p["lesson"] for p in paths})])
    table(["", "mistake turns blocked", "naming its lesson", "false blocks (clean)", "errors"], [
        [k, f"{sum(map(ok, r[:n]))}/{n}", f"{sum(r[i] == p['lesson'] for i, p in enumerate(paths))}/{n}",
         f"{sum(map(ok, r[n:]))}/{len(clean)}", r.count("!error")] for k, r in res.items()])
    st1 = sum(any(by[o]["lesson"] == paths[i]["lesson"] for _, o in cands[i]) for i in range(n))
    print(f"  message stage found a path of the same lesson in the candidates {st1}/{n}; clean turns with no candidate "
          f"{sum(not cands[i] for i in range(n, len(items)))}/{len(clean)}")
    hit = next((i for i in range(n) if ok(dec[i])), None)
    none = next((i for i in range(n, len(items)) if dec[i] is None and cands[i]), None)
    for title, i in (("HIT", hit), ("CORRECT NONE", none)):
        if i is not None:
            trace(title, i, n, paths, clean, live, items, cands, by, out)
    print(f"wall clock {time.time() - t0:.0f} s, brain cache {mechbrain.STATS}\ndirect API {brain.STATS} (cache hits may be older claude -p answers)")


if __name__ == "__main__":
    main()
