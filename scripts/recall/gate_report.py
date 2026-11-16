"""Gate measurement from results/gate_verdicts.jsonl (verdicts.py): per rule the blocks sent, dropped (hedge or veto) and tokens,
the block rate (blocks sent / gate runs), and false-alarm candidates: a sent block after which the main session says
"false alarm" in its next replies. A candidate is for him to judge, not a verdict.
Usage: python -I scripts/recall/gate_report.py [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--log <file>]"""
import collections, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, verdicts

FALSE_ALARM = re.compile(r"false (alarm|block|positive)|wrongly blocked|shouldn't have blocked|gate was wrong", re.I)
LOOK_AHEAD = 3  # assistant messages after the block that are read for the words


def records(log, since="", until=""):
    out = []
    try:
        for l in open(log, encoding="utf-8"):
            try:
                r = json.loads(l)
            except ValueError:
                continue
            if (not since or r["ts"][:10] >= since) and (not until or r["ts"][:10] <= until):
                out.append(r)
    except OSError:
        pass
    return out


def sent(r):
    """A BLOCK record that reached the main session: not dropped by a veto, not a lesson verdict that leads with a hedge."""
    return r["verdict"] == "BLOCK" and not r["dropped"] and not (r["src"] == "lesson" and r["hedged"])


def alarms(recs):
    """[(ts, rules, snippet)]: sent gate blocks followed by a 'false alarm' remark of the main session."""
    out = []
    labelled = {(r["tp"], r["ref"]) for r in recs if r["src"] == "label"}  # already labelled by gatecases.label: not a candidate
    for g in (r for r in recs if r["src"] == "gate" and r["verdict"] == "SENT" and (r["tp"], r["n"]) not in labelled):
        rules = [f"{r['src']}:{r['rule']}" for r in recs if sent(r) and (r["tp"], r["n"]) == (g["tp"], g["n"])]
        texts = [x for e in ctx.entries(g["tp"])[g["n"]:] if e["type"] == "assistant"
                 for x in [b["text"] for b in ctx.blocks(e) if b.get("type") == "text"]][:LOOK_AHEAD]
        for t in texts:
            m = FALSE_ALARM.search(t)
            if m:
                out.append((g["ts"], rules, t[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")))
                break
    return out


def report(recs):
    runs = len({(r["tp"], r["n"]) for r in recs})  # one gate run = one transcript position (a run killed by its timeout has no final record)
    rows = collections.defaultdict(lambda: collections.Counter())
    for r in recs:
        if r["src"] != "gate" and r["verdict"] == "BLOCK":
            c = rows[f"{r['src']}:{r['rule']}"]
            c["sent" if sent(r) else "dropped"] += 1
            c["hedged"] += r["hedged"]
            c["tokens"] += r["tokens"]
    lines = [f"gate runs {runs}; blocks sent {len({(r['tp'], r['n']) for r in recs if sent(r)})}; "
             f"brain tokens {sum(r['tokens'] for r in recs)}",
             f"{'rule':44} {'sent':>5} {'dropped':>8} {'hedged':>7} {'rate':>7} {'tokens':>8}"]
    for k, c in sorted(rows.items(), key=lambda kv: -kv[1]["sent"]):
        lines.append(f"{k[:44]:44} {c['sent']:5d} {c['dropped']:8d} {c['hedged']:7d} {c['sent'] / runs if runs else 0:7.1%} {c['tokens']:8d}")
    al = alarms(recs)
    lines.append(f"labelled false alarms (the session said so, now cases in gate_eval_set.jsonl): {sum(r['src'] == 'label' for r in recs)}")
    lines.append(f"false-alarm candidates: {len(al)}")
    lines += [f"  {ts} {', '.join(rules) or '?'}: ...{s}..." for ts, rules, s in al]
    return "\n".join(lines)


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda n: a[a.index(n) + 1] if n in a else ""
    print(report(records(opt("--log") or verdicts.path(), opt("--since"), opt("--until"))))
