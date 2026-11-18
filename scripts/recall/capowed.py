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


def owe(kind, tp, prompt=None):
    es = [e for e in _load() if not (e["kind"] == kind and e["key"] == key(tp, prompt))]
    _save(es + [{"kind": kind, "tp": tp, "key": key(tp, prompt), "ts": time.time(), "paid": False, "blocked": False}])


def pay(kind):
    """A successful write: the newest unpaid marker of that kind is paid."""
    es = _load()
    for e in reversed(es):
        if e["kind"] == kind and not e["paid"]:
            e["paid"] = True
            break
    _save(es)


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
