"""Evals only (eval_mechanism.py): brain.ask cached by a hash of its exact (system, prompt) in results/mech_cache.jsonl, so an
unchanged arm or a repeated variant costs no model call on a re-run. Thread-safe; hits and misses are counted."""
import hashlib, json, os, threading
import brain, ctx

PATH = os.path.join(ctx.ROOT, "scripts", "recall", "results", "mech_cache.jsonl")
STATS = dict(hit=0, miss=0)
_lock, _real, _mem = threading.Lock(), brain.ask, {}


def _key(prompt, system):
    return hashlib.sha256((system + "\0" + prompt).encode("utf-8")).hexdigest()


def _cached(prompt, system="Answer tersely and exactly as instructed.", tag=""):
    k = _key(prompt, system)
    with _lock:
        if k in _mem:
            STATS["hit"] += 1
            return _mem[k], 0
    out, tok = _real(prompt, system, tag)  # errors are not cached
    with _lock:
        STATS["miss"] += 1
        _mem[k] = out
        with open(PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"k": k, "out": out}) + "\n")
    return out, tok


def install():
    try:
        for l in open(PATH, encoding="utf-8"):
            r = json.loads(l)
            _mem[r["k"]] = r["out"]
    except (OSError, ValueError):
        pass
    brain.ask = _cached


def graph_switch(on):
    """The graph-recall slot as on (True) or off (False) for this process, whatever slots.json says: eval only, never in the hooks."""
    real = getattr(ctx, "_enabled_real", ctx.enabled)
    ctx._enabled_real = real
    ctx.enabled = lambda slot: on if slot == "graph-recall" else real(slot)
