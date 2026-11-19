"""Evals only (eval_mechanism.py, part b): the gate's real lesson check (gate.check: retrieval, then the real cheap model) on a
rebuilt assistant turn, with the switch off or on. The occurrence's own path is held out of retrieval (gate.check exclude)."""
import os, tempfile
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("RECALL_VERDICT_LOG", os.path.join(tempfile.mkdtemp(prefix="mech-v-"), "verdicts.jsonl"))  # never the real log
import ctx, gate, graph, mechbrain


def run(turns, arm, workers=16):
    """turns: [{tp, key (occurrence key or None)}]. -> [cid the gate blocked with, or None] in the same order. arm: None = off, else (graph.VARIANT, graph.REPLY_KINDS)."""
    mechbrain.graph_switch(arm is not None)
    if arm:
        graph.VARIANT, graph.REPLY_KINDS = arm
    ctx.BUDGET = 10 ** 9  # the hook's time budget does not apply to an eval
    ex = lambda t: {t["key"]} if t.get("key") else set()
    for t in turns:  # one thread first: it fills the vector cache, so the threads below only read it
        text, tools = ctx.last_turn(t["tp"])
        gate.candidates(text, tools, ex(t))

    def one(t):
        for _ in range(2):  # a transient failure of the cheap model is retried once
            try:
                r = gate.check(t["tp"], ex(t))
                return r[0][0] if r else None
            except Exception as e:
                err = e
        ctx.log(f"eval_mechanism: gate check failed twice: {err!r}")
        return "!error"

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(one, turns))
