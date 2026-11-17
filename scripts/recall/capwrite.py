"""The session writes the mistake case, not the cheap model: it has the context. The hook tells it to (instruction()), it
runs `capture.py write <json>` (write()); capowed.py tracks that it did."""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capowed, clean, ctx, history, index, pending

PENDING = os.path.join(index.CASES, "_pending")
SCANNED = ("situation", "did", "disliked", "lesson", "slug")  # his_words stays local (history.db, the gitignored pending draft)
SHOWN = 10


def lessons():
    """[(id, lesson)] of the approved and the pending cases."""
    out = []
    for d in (index.CASES, PENDING):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".md") and f != "README.md":
                out.append((f[:-3], index.parse(os.path.join(d, f)).get("lesson", "")))
    return out


def _closest(why, ls):
    """The SHOWN lessons nearest (embedding) to the detector's guess; the first ones if embedding fails."""
    try:
        import embed
        sc = embed.scores(why, {i: [l] for i, l in ls})
        return sorted(ls, key=lambda x: -sc.get(x[0], 0))[:SHOWN]
    except Exception as e:
        ctx.log(f"capture: lessons not ranked: {e!r}")
        return ls[:SHOWN]


def instruction(why, tp, prompt):
    """The line hook.py prints to the session; also marks his message as owing a write."""
    capowed.owe("correction", tp, prompt)
    near = "\n".join(f"- {i}: {l[:110]}" for i, l in _closest(why, lessons()))
    return ("Capture: his message may correct your previous turn (the detector's guess, not a fact: " + why + "). If it does, "
            "write it now with what you know from this session: `python -I scripts/recall/capture.py write <json file>` with "
            "JSON {situation, did, disliked, his_words, and either lesson + slug (new) or lesson_id (repeat)}. Situation = the "
            "context (what was being worked on, what had just been done, its state) + what he asked; did = what you did; "
            "disliked = what he didn't like (his words); lesson = a general principle. If this repeats an existing lesson, give "
            "its id instead of a new lesson. Unknown part -> \"(not stated)\", never a guess. No names, paths or file names. If "
            "it is not a mistake: `python -I scripts/recall/capture.py write --none \"<why>\"`. Closest lessons (`python -I "
            "scripts/recall/capture.py lessons` lists all):\n" + near)


def none(why):
    """The session says the detector was wrong: logged, no case, the debt is paid."""
    if not why.strip():
        return False, "give the reason it is not a mistake"
    ctx.log(f"capture: detector YES settled as not a mistake: {why.strip()}")
    capowed.pay("correction")
    return True, "logged, no case written"


def _find(cid):
    for d in (index.CASES, PENDING):
        p = os.path.join(d, cid + ".md")
        if os.path.exists(p):
            return p
    return None


def write(d):
    """Validate and save what the session wrote. Returns (ok, message)."""
    if not isinstance(d, dict):
        return False, "the JSON must be an object"
    src, lid = d.get("source", "correction"), d.get("lesson_id")
    if src not in ("correction", "gate") or (src == "gate" and not lid):
        return False, "source is correction or gate; a gate catch needs lesson_id"
    need = ("situation", "did", "disliked") + (("his_words",) if src == "correction" else ()) + (("lesson_id",) if lid else ("lesson", "slug"))
    miss = [k for k in need if not str(d.get(k, "")).strip()]
    if miss:
        return False, f"missing or empty: {', '.join(miss)} (an unknown part is \"(not stated)\")"
    if lid and not _find(lid):
        return False, f"no lesson with id {lid!r}"
    hits = [f"{k}: {v}" for k in SCANNED for v in clean.violations(str(d.get(k, "")), strict=True)]
    if hits:
        return False, "privacy scan hit, rewrite in general words: " + "; ".join(hits)
    c = json.dumps({"situation": d["situation"], "assistant_did": d["did"], "disliked": d["disliked"]})
    raw = d["his_words"].strip() if src == "correction" else d["disliked"]  # a gate catch: the gate's reason is the raw text
    if lid:
        history.record(_find(lid), src, raw, clean_text=c)
        capowed.pay(src)
        return True, f"occurrence recorded on {lid}"
    q, slug = pending.q, pending.slugify(d["slug"], "captured-mistake")
    path = os.path.join(PENDING, slug + ".md")
    os.makedirs(PENDING, exist_ok=True)
    open(path, "w", encoding="utf-8").write(
        f"---\nid: {slug}\ndate: {datetime.date.today()}\nsource: written by the session\nstatus: pending\nasked: false\n"
        f"level: advice\nhis_words: {q(raw)}\nsituation:\n  - {q(d['situation'])}\nwrong: {q(d['did'])}\n"
        f"right: {q('(not stated)')}\nlesson: {q(d['lesson'])}\nreplay: {q('(not stated)')}\npass_if:\n  - {q('(not stated)')}\n"
        "occurrences: 0\n---\n")
    history.record(path, src, raw, clean_text=c)
    capowed.pay(src)
    try:
        pending.todo_add(f"- [ ] review captured case `{slug}` (cases/_pending/{slug}.md): add, edit or discard")
    except OSError as e:
        ctx.log(f"capture: todo not updated: {e!r}")
    return True, f"pending case written: cases/_pending/{slug}.md"
