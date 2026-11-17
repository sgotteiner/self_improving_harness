"""Does the graph mechanism (slot graph-recall) beat the flat one? Off vs on, counts n/N. Needs the real cheap model for b, c
(calls are concurrent and cached by prompt in results/mech_cache.jsonl). Usage: python -I scripts/recall/eval_mechanism.py [free]
 a. retrieval (eval_variants.py, free): held-out per step against flat and flat-split, each with its own cutoff, twins excluded, bias.
 b. catching: the gate's lesson check (gate.check, real model) on the rebuilt assistant turn of each real occurrence (the gate's
    own path held out), and on turns without an occurrence (false blocks). Arms: off and the ARMS below.
 c. capture: each known correction replayed as new -> attached to its own lesson / a wrong one / a new draft, per attach mode.
The decision line is the owner's rule; the slot is set by hand from it."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_variants, graph, mechbrain, mechcapture, mechcatch, mechturns

mechbrain.install()
ARMS = {"on:norm2+lesson": ("norm2", ("action", "path", "lesson")), "on:best+lesson": ("best", ("action", "path", "lesson"))}


def table(head, rows):
    w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
    for r in [head] + rows:
        print("  " + "  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))


def part_b(occ):
    lessons = {p["key"]: p["lessons"] for p in graph.occurrences()}
    have = [o for o in occ if o["tp"]]
    clean = mechturns.clean_turns(occ)
    print(f"\n(b) catching: {len(have)} of {len(occ)} occurrences have a rebuilt turn; {len(clean)} clean turns")
    turns = [dict(tp=o["tp"], key=o["key"]) for o in have] + [dict(tp=c["tp"]) for c in clean]
    res = {}
    for name, arm in dict(off=None, **ARMS).items():
        g = mechcatch.run(turns, arm)
        c = g[:len(have)]
        ok = lambda x: x is not None and x != "!error"
        res[name] = (sum(map(ok, c)), sum(map(ok, g[len(have):])))
        print(f"    {name}: blocks {res[name][0]}/{len(have)} occurrences (naming one of its lessons: "
              f"{sum(x in lessons[o['key']] for x, o in zip(c, have))}); false blocks {res[name][1]}/{len(clean)}; model errors {g.count('!error')}")
    return res, len(have), len(clean)


def main():
    t0 = time.time()
    occ = mechturns.occurrence_turns()
    turns = {o["key"]: o["tp"] for o in occ if o["tp"]}
    eval_variants.show(*eval_variants.run(turns, [c["tp"] for c in mechturns.clean_turns(occ)]))
    if "free" in sys.argv[1:]:
        return print(f"\nfree part: {time.time() - t0:.0f} s")
    b, n, nc = part_b(occ)
    reps = mechcapture.corrections(occ)
    lessons = {p["key"]: p["lessons"] for p in graph.occurrences()}
    print("\n(c) capture: each known correction replayed as new (own path held out): attached to its own lesson | a wrong one | new draft")
    for mode, r in mechcapture.attach(reps, lessons).items():
        print(f"    {mode:7} own {r[0]} | wrong {r[1]} | new draft {r[2]}  (of {r[3]})")
    d, nd = mechcapture.drafts()
    print(f"    pending drafts (new mistakes) wrongly attached to another lesson, of {nd}: " + ", ".join(f"{m} {v}" for m, v in d.items()))
    print("\nDECISION: switch ON only if no number is worse than off. catches/false blocks off %s -> %s of %d/%d" % (
        b["off"], {k: v for k, v in b.items() if k != "off"}, n, nc))
    print(f"wall clock {time.time() - t0:.0f} s, brain cache {mechbrain.STATS}")


if __name__ == "__main__":
    main()
