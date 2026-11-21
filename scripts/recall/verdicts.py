"""Every gate verdict, one JSON line each in results/gate_verdicts.jsonl (gitignored): so the block rate and the false alarms
can be measured (gate_report.py) instead of remembered. A record: ts, tp (transcript), n (its entry count at that moment, the
position the report reads from), src (lesson | delegation | gate), verdict (OK | BLOCK | SENT | PASS), rule (case id or
delegation kind), hedged, dropped (why a BLOCK was not sent), skip (why the brain was not asked), tokens, features (a
delegation BLOCK: the counted facts of the turn, booleans and agent types only), ref (a label: the position of the block it marks), score (a lesson verdict: the model's 1-5 relevance).
Never fails the gate: a write error is ignored."""
import datetime, json, os

import ctx

PATH = os.path.join(ctx.ROOT, "scripts", "recall", "results", "gate_verdicts.jsonl")


def path():
    return os.environ.get("RECALL_VERDICT_LOG") or PATH  # the tests point it at a temp file


def log(tp, src, verdict, rule="", hedged=False, dropped="", skip="", tokens=0, features=None, ref=None, score=None):
    try:
        rec = dict(ts=datetime.datetime.now().isoformat(timespec="seconds"), tp=tp, n=len(ctx.entries(tp)) if tp else 0, src=src,
                   verdict=verdict, rule=rule, hedged=bool(hedged), dropped=dropped, skip=skip, tokens=tokens,
                   features=features, ref=ref, score=score)
        with open(path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        ctx.log(f"verdicts: not written: {e!r}")
