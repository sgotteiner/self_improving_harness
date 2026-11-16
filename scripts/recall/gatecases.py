"""The gate learns from its false alarms. When the main session's reply says a block was a false alarm, the verdict log marks
that block as a labelled false alarm (a `label` record) and the turn's counted facts become a regression case in
gate_eval_set.jsonl (eval_gate.py replays them). A case holds only booleans and agent types, never words of his or of the turn,
so the tracked file stays clean. Called by gate.py before anything else, also on the reply that follows a block."""
import hashlib, json, os, re

import ctx, gate_report, verdicts

SET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate_eval_set.jsonl")
FALSE_ALARM = gate_report.FALSE_ALARM
KIND = r"false (alarm|block|positive)"
NOT_A_CLAIM = re.compile(r"\b(not|no|isn't|wasn't|aren't|never|nor)\b[^.;]{0,25}" + KIND + r"|\b(if|were|would|whether|unless|could|might|maybe|perhaps)\b[^.;]{0,40}"
                         + KIND + "|" + KIND + r"[^.;]{0,15}\b(if|would|could|might)\b", re.I)
WORDS = {"LOOP": "loop", "TESTER-HERE": "test suite|suite|main session|test command", "TESTER": "tester|no test|not tested|test ran",
         "REVIEWER": "review", "KNOWLEDGE-MANAGER": "knowledge|sdd|docs?\\b", "SETUP-MANAGER": "setup.manager|commit|uncommitted"}  # how a reply names a rule


def claimed(sentence):
    """True when a sentence itself claims a block was a false alarm: not "this is not a false alarm", not "if it were a false alarm"."""
    return bool(FALSE_ALARM.search(sentence)) and not NOT_A_CLAIM.search(sentence)


def add_case(block):
    """Append the labelled block as a no_block case unless it is there already; returns its id or None. A case whose rule and
    facts are already a real block (expect: block) is a contradiction: it is logged, not added."""
    f = block.get("features")
    if not f or block["rule"] == "TESTER-HERE":  # TESTER-HERE misfires are a command read wrongly: suitecmd's command tests cover them
        return None  # a lesson verdict or an older record: nothing countable to replay
    cid = f"{block['ts'][:10]}-{block['rule'].lower()}-" + hashlib.sha1(json.dumps([block["rule"], f], sort_keys=True).encode()).hexdigest()[:6]
    try:
        cases = [json.loads(l) for l in open(SET, encoding="utf-8") if l.strip()]
    except OSError:
        cases = []
    if cid in {c["id"] for c in cases}:
        return None
    clash = next((c["id"] for c in cases if c["expect"] == "block" and c["rule"] == block["rule"] and c["features"] == f), None)
    if clash:
        ctx.log(f"gatecases: labelled false alarm {block['rule']} not added: the same facts are the real block {clash}")
        return None
    with open(SET, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(id=cid, rule=block["rule"], expect="no_block", hedged=block["hedged"], source="labelled false alarm",
                                 features=f), sort_keys=True) + "\n")
    return cid


def _claims(tp):
    """[(entry index, sentence)] of the latest turn's replies that claim a false alarm."""
    es = ctx.entries(tp)
    return [(i, s) for i in range(ctx._start(es, None), len(es)) if es[i]["type"] == "assistant"
            for b in ctx.blocks(es[i]) if b.get("type") == "text" for s in re.split(r"(?<=[.!?])\s+|\n+", b["text"]) if claimed(s)]


def label(tp):
    """Label the blocks that the latest turn's replies call a false alarm; returns the labelled rules, or None. A sentence at
    entry i can only label a block logged at a position n <= i (it was said after that block, never about a later one). Of those
    the latest unlabelled block whose rule the sentence names ("a false alarm from the loop rule"); naming none, the latest one
    if it was a single block (several and no name: ambiguous, nothing is labelled)."""
    claims = _claims(tp)
    if not claims:
        return None
    recs = gate_report.records(verdicts.path())
    done = {r["ref"] for r in recs if r["src"] == "label" and r["tp"] == tp}
    out = []
    for i, sentence in claims:
        ns = sorted({g["n"] for g in recs if g["src"] == "gate" and g["verdict"] == "SENT" and g["tp"] == tp and g["n"] <= i and g["n"] not in done}, reverse=True)
        groups = [[b for b in recs if b["tp"] == tp and b["n"] == n and gate_report.sent(b) and b["src"] != "gate"] for n in ns]
        groups = [g for g in groups if g]
        named = lambda b: re.search(WORDS.get(b["rule"], "$^"), sentence, re.I)
        pick = next(([b for b in g if named(b)] for g in groups if any(named(b) for b in g)), None)
        pick = pick or (groups[0] if groups and len(groups[0]) == 1 else None)
        if pick:
            rules = [f"{b['src']}:{b['rule']}" for b in pick]
            verdicts.log(tp, "label", "FALSE_ALARM", rule=",".join(rules), ref=pick[0]["n"])
            done.add(pick[0]["n"])
            for b in pick:
                add_case(b)
            out += rules
    return out or None
