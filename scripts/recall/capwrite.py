"""The session writes the mistake case, not the cheap model: it has the context. The hook tells it to (instruction()), it
runs `capture.py write <json>` (write()); capowed.py tracks that it did."""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capowed, clean, ctx, history, index, patchfirst, pending, tracechange

PENDING = os.path.join(index.CASES, "_pending")
SCANNED = ("situation", "did", "disliked", "lesson", "slug")  # his_words stays local (history.db, the gitignored pending draft)
SHOWN = 10
SUCCESS = "success"  # a source like correction and gate: what he liked, not what he disliked (stored in the same `disliked` slot, as work does)
SOURCES = ("correction", "gate", SUCCESS)
OWN_WORDS = ("correction", SUCCESS)  # sources whose raw text is his message


def lessons():
    """[(id, lesson)] of the approved and the pending cases."""
    out = []
    for d in (index.CASES, PENDING):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".md") and f not in index.NOT_LESSONS:
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


def _near(why):
    return "\n".join(f"- {i}: {l[:110]}" for i, l in _closest(why, lessons()))


def success_instruction(why, tp, prompt):
    """The line hook.py prints when the message step guessed he praised the previous turn (praise.py); marks it as owing a write."""
    capowed.owe(SUCCESS, tp, prompt)
    return ("Capture (success): his message may praise your previous turn (the detector's guess, not a fact: " + why + "). If it does, "
            "write it now with what you know from this session: `python -I scripts/recall/capture.py write <json file>` with JSON "
            "{source: \"success\", situation, did, liked, his_words, and either lesson + slug (new) or lesson_id (repeat)}. Situation = "
            "the context (what was being worked on, what had just been done, its state) + what he asked; did = what you did; liked = "
            "what he liked (his words); lesson = a general principle to keep doing. If this repeats an existing lesson, give its id "
            "instead of a new lesson. Unknown part -> \"(not stated)\", never a guess. No names, paths or file names. If it is not "
            "praise: `python -I scripts/recall/capture.py write --none \"<why>\" --success`. Closest lessons (`python -I "
            "scripts/recall/capture.py lessons` lists all):\n" + _near(why))


def instruction(why, tp, prompt):
    """The line hook.py prints to the session; also marks his message as owing a write."""
    capowed.owe("correction", tp, prompt)
    near = _near(why)
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
    if src not in SOURCES or (src == "gate" and not lid):
        return False, "source is correction, gate or success; a gate catch needs lesson_id"
    judged = "liked" if src == SUCCESS else "disliked"
    need = ("situation", "did", judged) + (("his_words",) if src in OWN_WORDS else ()) + (("lesson_id",) if lid else ("lesson", "slug"))
    miss = [k for k in need if not str(d.get(k, "")).strip()]
    if miss:
        return False, f"missing or empty: {', '.join(miss)} (an unknown part is \"(not stated)\")"
    d = {**d, "disliked": d[judged]}  # the shared store has one slot for the outcome (index.label shows it by source); scanned there, once
    if lid and not _find(lid):
        return False, f"no lesson with id {lid!r}"
    if src == "gate" and capowed.check_gate(lid):
        return False, capowed.check_gate(lid)
    hits = [f"{k}: {v}" for k in SCANNED for v in clean.violations(str(d.get(k, "")), strict=True)]
    if hits:
        return False, "privacy scan hit, rewrite in general words: " + "; ".join(hits)
    c = json.dumps({"situation": d["situation"], "assistant_did": d["did"], "disliked": d["disliked"]})
    raw = d["his_words"].strip() if src in OWN_WORDS else d["disliked"]  # a gate catch: the gate's reason is the raw text
    if lid:
        sid = history.record(_find(lid), src, raw, clean_text=c)
        tracechange.link_situations(capowed.pay(src), [sid], src, lid)
        if src == "gate":
            _count(lambda: capowed.settle_one(lid))
        else:  # a missed repeat (missed) or repeated praise (liked), and the closest situation of the lesson (the one just stored is left out)
            patchfirst.repeated(lid, d, src, lambda r: (r["situation"], r["did"]) == (d["situation"], d["did"]))
        return True, f"occurrence recorded on {lid}"
    slug = pending.slugify(d["slug"], pending.DEFAULT_SLUG)
    if d.get("approved") is not True:  # no drafts: only his yes adds a lesson (or edits the lesson this one repeats)
        paid, sids = capowed.pay(src), []
        try:
            msg = patchfirst.propose(d, src, raw, c, sids, paid)
            tracechange.link_situations(paid, sids, src, None)
            return True, msg
        except Exception as e:  # the queue failed: the session asks him itself, as before
            ctx.log(f"capture: proposal not queued: {e!r}")
            return True, ("Ask him in your reply, with the exact lesson line; only his yes adds it: rerun with \"approved\": true. "
                          f"Lesson: {d['lesson']}")
    path = os.path.join(index.CASES, slug + ".md")
    open(path, "w", encoding="utf-8").write(pending.case_text(slug, d, raw, datetime.date.today()))
    sid = history.record(path, src, raw, clean_text=c)
    tracechange.link_situations(capowed.pay(src), [sid], src, slug)
    return True, f"case written: cases/{slug}.md"
