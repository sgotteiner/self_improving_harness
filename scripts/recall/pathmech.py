"""The owner's path mechanism tried as he described it (offline, no live hook change). Usage: python -I scripts/recall/pathmech.py
Cases are paths; their sections are nodes (situation, what you did, what he did not like, lesson), each with its own embedding.
Message stage: the live situation (the template: Working on / Just done / State / He asked) vs SITUATION nodes. Reply stage: the
turn's plan and actions vs the DID nodes of the candidate paths. Decision: the brain sees the matched paths and says VIOLATION or OK.
A = stored situations written by the agent from the transcripts, live one by the brain; B = both by the brain.
Measure: held-out (the query's own path removed) past mistake turns blocked, and false blocks on clean turns, vs today's gate."""
import os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mechcatch  # first: it points the verdict log at a temp file
import ctx, embed, index, mechbrain, mechturns, pathparts as pp

mechbrain.install()
ctx.BUDGET = 10 ** 9
cut = lambda s, n=170: " ".join(str(s).split())[:n] + ("..." if len(" ".join(str(s).split())) > n else "")

SPEC = """SPEC CHECK (query text -> node kind it is compared with)
 message stage: query = the live situation in the template, written by the brain (Haiku) from the last 4 turns + his message;
                compared with: SITUATION nodes only (A: written by the agent; B: written by the brain the same way). Top %d above %.2f.
 reply stage:   query = the assistant turn's final message + its tool calls (chunks); compared with: the DID nodes of those
                candidate paths only. Above %.2f = the path matches.
 decision:      the brain gets the turn + each matched path's situation, did, his complaint (or the gate reason, marked), lesson."""


def table(head, rows):
    w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
    for r in [head] + rows:
        print("  " + "  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))


def main():
    t0 = time.time()
    print(SPEC % (pp.N, pp.CUT, pp.CUT))
    paths = pp.load()
    by = {p["occ"]: p for p in paths}
    clean = [dict(name=c["name"], tp=c["tp"], **dict(zip(("tt", "tp_msg"), pp.turn_of(c["tp"]))))
             for c in mechturns.clean_turns(None)]
    keys = {(o["cid"], o["text"]): o["key"] for o in mechturns.occurrence_turns()}  # the gate's held-out keys
    turns = [dict(tp=p["tp"], key=keys.get((p["lesson"], p["raw"]))) for p in paths] + [dict(tp=c["tp"]) for c in clean]
    base = {}
    with ThreadPoolExecutor(32) as ex:
        live = list(ex.map(pp.render, [p["tp_msg"] for p in paths] + [c["tp_msg"] for c in clean]))
        sitB = list(ex.map(pp.render, [p["tp_msg"] for p in paths]))
    lessons = {os.path.basename(f)[:-3]: index.meta(os.path.basename(f)[:-3])[2] for f in index.case_files()}
    g, lv = pp.nodes(paths, lessons)
    print(f"\nnodes: {len(paths)} situation (x2 versions: A, B) + {len(paths)} did + {len(paths)} complaint + {len(lv)} lesson, "
          f"each its own embedding; edges: {len(paths)} paths -> their lesson")
    sit = dict(A={o: v["situation"] for o, v in g.items()}, B=dict(zip(g, embed.encode(sitB))))
    did = {o: v["did"] for o, v in g.items()}
    items = [(p["tp"], p["text"], p["tools"], p["occ"]) for p in paths] + [(c["tp"], *c["tt"], None) for c in clean]
    plan = {a: [] for a in sit}  # arm -> per turn (candidates, matched)
    for a in sit:
        for (tp, text, tools, occ), lv_ in zip(items, live):
            cands = pp.at_message(lv_, sit[a], occ)
            plan[a].append((cands, pp.at_reply(text, tools, did, cands)))
    ex_i = next((i for i in range(len(paths)) if plan["A"][i][1]), 0)
    cs, ms = plan["A"][ex_i]
    p = paths[ex_i]
    print(f"\nTRACED EXAMPLE (A, held out: path {p['occ']}, lesson {p['lesson']})\n  live situation (brain): {cut(live[ex_i])}")
    for s, o in cs[:1]:
        q = by[o]
        print(f"  -> matched situation node {s:.2f} of path {o}: {cut(q['situation'])}\n  -> its did node: {cut(q['did'])}")
        print(f"  -> turn vs that did node: {dict((x, round(y, 2)) for y, x in ms).get(o, 'below cutoff')}\n  -> his complaint: {cut(q['complaint'])}"
              f"\n  -> lesson {q['lesson']}: {cut(lessons[q['lesson']])}")
    th = threading.Thread(target=lambda: base.update(r=mechcatch.run(turns, None)))  # today's gate, parallel with the decisions
    th.start()  # (started after all embedding here is done: the gate's own retrieval then has the vector cache to itself)
    with ThreadPoolExecutor(32) as ex:
        dec = {a: list(ex.map(lambda x: pp.decide(x[0][1], x[0][2], plan[a][x[1]][1], by), [(it, i) for i, it in enumerate(items)])) for a in sit}
    th.join()
    ok = lambda x: x is not None and x != "!error"
    n = len(paths)
    res = dict(off=base["r"], **{"mech " + a: dec[a] for a in sit})
    print("\nMEASURE (held-out; mistake turns blocked | false blocks on clean turns)")
    table(["lesson", "turns"] + list(res), [[les, sum(p["lesson"] == les for p in paths)] + [
        sum(ok(r[i]) for i, p in enumerate(paths) if p["lesson"] == les) for r in res.values()] for les in sorted({p["lesson"] for p in paths})])
    table(["", "mistake turns blocked", "naming its lesson", "false blocks (clean)", "errors"], [
        [k, f"{sum(map(ok, r[:n]))}/{n}", f"{sum(r[i] == p['lesson'] for i, p in enumerate(paths))}/{n}",
         f"{sum(map(ok, r[n:]))}/{len(clean)}", r.count("!error")] for k, r in res.items()])
    for a in sit:
        st1 = sum(any(by[o]["lesson"] == paths[i]["lesson"] for _, o in plan[a][i][0]) for i in range(n))
        st2 = sum(bool(plan[a][i][1]) for i in range(n))
        print(f"  {a}: message stage found a path of the same lesson in the candidates {st1}/{n}; reply stage matched a did node "
              f"{st2}/{n}; clean turns with a match {sum(bool(plan[a][i][1]) for i in range(n, len(items)))}/{len(clean)}")
    print(f"wall clock {time.time() - t0:.0f} s, brain cache {mechbrain.STATS}")


if __name__ == "__main__":
    main()
