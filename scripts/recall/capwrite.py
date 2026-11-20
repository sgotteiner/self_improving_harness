"""The session writes the mistake case, not the cheap model: it has the context. The hook tells it to (instruction()), it
runs `capture.py write <json>` (write()); capowed.py tracks that it did."""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capowed, capstats, clean, ctx, history, index, pending

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


def none(why, kind="correction"):
    """The session says the detector (kind correction) or the gate (kind gate) was wrong: logged, no case, the debt is paid."""
    if not why.strip():
        return False, "give the reason it is not a mistake"
    ctx.log(f"capture: {kind} settled as not a mistake: {why.strip()}")
    capowed.pay(kind)
    if kind == "gate":
        _count(capowed.settle_rest)  # the markers only; the count is his verdict (capverdict.py)
    return True, "logged, no case written"


def _count(f):
    """A failed count never fails a write or a settlement that already happened."""
    try:
        f()
    except Exception as e:
        ctx.log(f"capture: count failed: {e!r}")


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
    if src == "gate" and capowed.check_gate(lid):
        return False, capowed.check_gate(lid)
    hits = [f"{k}: {v}" for k in SCANNED for v in clean.violations(str(d.get(k, "")), strict=True)]
    if hits:
        return False, "privacy scan hit, rewrite in general words: " + "; ".join(hits)
    c = json.dumps({"situation": d["situation"], "assistant_did": d["did"], "disliked": d["disliked"]})
    raw = d["his_words"].strip() if src == "correction" else d["disliked"]  # a gate catch: the gate's reason is the raw text
    if lid:
        history.record(_find(lid), src, raw, clean_text=c)
        capowed.pay(src)
        _count(lambda: capstats.bump(lid, "missed") if src != "gate" else capowed.settle_one(lid))
        return True, f"occurrence recorded on {lid}"
    slug = pending.slugify(d["slug"], "captured-mistake")
    if d.get("approved") is not True:  # no drafts: only his yes adds a lesson
        capowed.pay(src)
        return True, ("Ask him in your reply, with the exact lesson line; only his yes adds it: rerun with \"approved\": true. "
                      f"Lesson: {d['lesson']}")
    q, path = pending.q, os.path.join(index.CASES, slug + ".md")
    open(path, "w", encoding="utf-8").write(
        f"---\nid: {slug}\ndate: {datetime.date.today()}\nlevel: advice\nhis_words: {q(raw)}\nsituation:\n  - {q(d['situation'])}\n"
        f"wrong: {q(d['did'])}\nright: {q('(not stated)')}\nlesson: {q(d['lesson'])}\nreplay: {q('(not stated)')}\n"
        f"pass_if:\n  - {q('(not stated)')}\noccurrences: 0\n---\n")
    history.record(path, src, raw, clean_text=c)
    capowed.pay(src)
    return True, f"case written: cases/{slug}.md"
