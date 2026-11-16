"""Replays every case of gate_eval_set.jsonl through the gate's decision and reports false alarms caught / real blocks kept.
A case: the block the brain asked for (`rule`), the counted facts of the turn (`features`, booleans and agent types), whether the
brain's reason hedged, and what must happen (`expect`: no_block = a false alarm that must not be sent, block = a real one that must).
Default: no model; the brain's verdict is the recorded `rule` and only the code's vetoes are replayed (free, deterministic).
--real: a case that has a `scenario` (cleaned text of a turn: human, tools, text, facts) is also given to the real cheap model
with the delegation draft's Output step prompt, and its fresh verdict goes through the same vetoes.
A case with "known_gap": true is a false alarm the gate lets through on purpose: the round-2 veto "the final message announces the
review as the next step" was removed (too wide: "No review was done before the commit" matched it). It is listed, not failed.
Cases come from labelled false alarms (gatecases.py, automatic) and from the seeds written by hand.
Usage: python -I scripts/recall/eval_gate.py [--real]    exit 1 if any case goes the wrong way"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, delegate, delegvet, gatecases, turnfacts


def decide(kind, hedged, f):
    """What the gate sends for a brain verdict `kind` (None = OK) on a turn with facts `f`: a kind, or None."""
    if f.get("suite_unexcused"):
        return "TESTER-HERE"  # counted from the Bash calls: no brain involved
    if not kind:
        return None
    return None if delegvet.veto(kind, "unclear" if hedged else "x", f) else kind


def brain_kind(sc):
    """The fresh verdict of the real cheap model on a scenario: (kind or None, hedged)."""
    import brain
    p = delegate._fill(delegate._prompt("Output step"), rules=delegate.rules(), human=sc["human"], tools=sc["tools"], text=sc["text"],
                       facts=sc["facts"], max_rounds=str(turnfacts.ROUNDS_MAX))
    out, _ = brain.ask(p, tag="eval-gate")
    m = re.match(r"\s*BLOCK\s+([A-Z-]+)\s*\|?\s*(.*)", out, re.S)
    return (m.group(1), ctx.hedged(m.group(2))) if m else (None, False)


def run(cases, real=False):
    """[(id, ok, got)] for each case."""
    out = []
    for c in cases:
        kind, hedged = (c["rule"], c.get("hedged", False))
        if real and c.get("scenario"):
            kind, hedged = brain_kind(c["scenario"])
        got = decide(kind, hedged, c["features"])
        want = None if c["expect"] == "no_block" else c["rule"]
        out.append((c["id"], got == want, got))
    return out


def load(path=gatecases.SET):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


if __name__ == "__main__":
    cases, real = load(), "--real" in sys.argv
    if real:
        ctx.BUDGET = 10 ** 6  # a manual run: no hook budget
    res = run(cases, real)
    for cid, ok, got in res:
        if not ok:
            print(f"BAD {cid}: the gate sent {got}")
    gaps = {c["id"] for c in cases if c.get("known_gap")}  # false alarms the gate no longer prevents, on purpose (see below)
    for cid, ok, got in res:
        if not ok and cid in gaps:
            print(f"known gap {cid}: the gate sends {got}")
    ok_ids = {r[0] for r in res if r[1]}
    fa = [c for c in cases if c["expect"] == "no_block"]
    rb = [c for c in cases if c["expect"] == "block"]
    print(f"gate eval{' (real brain on ' + str(sum(1 for c in cases if c.get('scenario'))) + ' scenarios)' if real else ''}: "
          f"false alarms caught {sum(c['id'] in ok_ids for c in fa)}/{len(fa)}, real blocks kept {sum(c['id'] in ok_ids for c in rb)}/{len(rb)}"
          f"{', known gaps ' + str(len(gaps - ok_ids)) if gaps - ok_ids else ''}")
    sys.exit(0 if len(ok_ids | gaps) == len(cases) else 1)
