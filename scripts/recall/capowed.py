"""Who owes a `capture.py write`: one marker per his message (hash of the human prompt + transcript path) for a detected
correction, one per transcript for a gate catch. Paid by a successful write (capwrite), never by reading tool lines, so a write
made before a background-notice restart still counts. The output gate blocks on an unpaid marker once; it fails open."""
import hashlib, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

OWED = os.path.join(ctx.ROOT, "scripts", "recall", "results", "capture_owed.json")
DAY = 86400
REASON = {"correction": "Capture: his message corrected you and the case was not written. Run `python -I scripts/recall/capture.py "
                        "write <json file>` now (situation, did, disliked, his_words, lesson + slug or lesson_id), or `capture.py "
                        "write --none \"<why it is not a mistake>\"` if the detector was wrong, then finish.",
          "gate": "Capture: the output gate caught a known mistake earlier and no occurrence was recorded. Run `python -I "
                  "scripts/recall/capture.py write <json file>` with source \"gate\" and lesson_id, or `capture.py write --none \"<why the "
                  "block was a false alarm>\" --gate` if it was, then finish."}


def key(tp, prompt=None):
    """Id of his message: the prompt given, else the last human message of the transcript."""
    if prompt is None:
        prompt = next((ctx.human_text(e) for e in reversed(ctx.entries(tp)) if ctx.human_text(e)), "")
    return hashlib.sha1((prompt.strip() + "\n" + tp).encode("utf-8")).hexdigest()[:16]


def _load():
    try:
        es = json.load(open(OWED, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [e for e in es if isinstance(e, dict) and time.time() - e.get("ts", 0) < DAY]  # older than a day: pruned


def _save(es):
    os.makedirs(os.path.dirname(OWED), exist_ok=True)
    json.dump(es, open(OWED, "w", encoding="utf-8"))


def owe(kind, tp, prompt=None, lesson=None):
    """lesson (a gate marker): the lesson the block was on, kept so a false-alarm settlement knows it; several in one block add up."""
    old = [e for e in _load() if e["kind"] == kind and e["key"] == key(tp, prompt) and not e["paid"]]
    ls = sorted({l for e in old for l in e.get("lessons", [])} | ({lesson} if lesson else set()))
    done = sorted({l for e in old for l in e.get("settled", [])})
    es = [e for e in _load() if not (e["kind"] == kind and e["key"] == key(tp, prompt))]
    _save(es + [{"kind": kind, "tp": tp, "key": key(tp, prompt), "ts": time.time(), "paid": False, "blocked": False, "lessons": ls, "settled": done}])


def pay(kind):
    """A successful write: the newest unpaid marker of that kind is paid and returned (None if there was none)."""
    es, paid = _load(), None
    for e in reversed(es):
        if e["kind"] == kind and not e["paid"]:
            e["paid"], paid = True, e
            break
    _save(es)
    return paid


def _gates():
    """The gate markers of the last day, newest first (a paid one too: its lessons may still be unsettled for the counts)."""
    return [e for e in reversed(_load()) if e["kind"] == "gate"]


def check_gate(lid):
    """Refusal text if gate blocks are still open and none of them named lid; else None."""
    ms = _gates()
    named = {l for e in ms for l in e.get("lessons", [])}
    open_ = sorted({l for e in ms for l in e.get("lessons", []) if l not in e.get("settled", [])})
    if open_ and lid not in named:
        return f"the gate block named {', '.join(open_)}, not {lid!r}: write source gate with one of those ids, or --none --gate"
    return None


def settle_one(lid):
    """A gate catch of lid recorded: True if it should count (the newest marker naming it had it unsettled, or no marker names it)."""
    es = _load()
    for e in reversed(es):
        if e["kind"] == "gate" and lid in e.get("lessons", []):
            if lid in e.get("settled", []):
                continue
            e["settled"] = e.get("settled", []) + [lid]
            _save(es)
            return True
    return not any(lid in e.get("lessons", []) for e in es if e["kind"] == "gate")


def settle_rest():
    """A false alarm: the unsettled lessons of the newest gate marker that has any (the one the block came from); all settled now."""
    es = _load()
    for e in reversed(es):
        left = [l for l in e.get("lessons", []) if l not in e.get("settled", [])] if e["kind"] == "gate" else []
        if left:
            e["settled"] = e.get("settled", []) + left
            _save(es)
            return left
    return []


def settle(tp, active):
    """Block reason (or None). A correction marker blocks only the stop of its own message; a gate marker the next stop of its
    transcript. Once each; the stop that follows a block (active) never blocks."""
    if active:
        return None
    es, cur = _load(), key(tp)
    for e in es:
        if e["tp"] != tp or e["paid"] or e["blocked"] or (e["kind"] == "correction" and e["key"] != cur):
            continue
        e["blocked"] = True
        _save(es)
        return REASON[e["kind"]]
    return None
