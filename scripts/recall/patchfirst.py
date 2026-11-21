"""Patch before create: a lesson the session wants to add is compared with every approved lesson in one cheap call. Same kind of
mistake as an existing lesson -> a proposal to reword that lesson, the situation attached to it; otherwise a new-lesson proposal.
His yes or ignore comes through proposals.py. A failed call counts as NEW (the check never blocks a write). Stdlib only."""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, capstats, clean, ctx, history, pending, proposals, situations, situtrace, views

COMPARE = ("Lessons an AI coding assistant learned from its mistakes (id: lesson. Right: what to do instead):\n{lessons}\n\n"
           "A new lesson was just drafted from a new mistake:\n{new}\n\nIs the new lesson the same kind of mistake as one of the "
           "lessons above (the same underlying behaviour, even when the wording or the situation differs), or a different kind? "
           "Reply with exactly one line: `SAME <id> | <that lesson reworded as ONE general sentence that also covers the new "
           "case>` or `NEW`.")
SAME = re.compile(r"\W*SAME\s+(\S+)\s*(?:\|\s*(.*))?", re.I)


def compare(lesson, situation=""):
    """-> (id, wording) when the lesson is the same kind of mistake as an approved one, else None. Raises if the call fails."""
    ls = views.lessons()
    if not ls:
        return None
    text = "\n".join(f"- {c}: {l} Right: {r}" for c, (_, l, r) in ls.items())
    out, _ = brain.ask(COMPARE.format(lessons=text, new=lesson + (f" (situation: {situation})" if situation else "")), tag="patch-first")
    m = SAME.match(out)
    cid = m.group(1).strip("`*<>.,|") if m else ""
    return (cid, (m.group(2) or "").strip(" `") or lesson) if cid in ls else None


def repeated(lid, d, src, same=lambda r: False):
    """His correction repeating lesson lid counts missed, his praise of it counts liked; either traces the closest situation (a hit).
    `same(row)` is true for the situation of this case if already stored (left out). Other sources count nothing. Fails open."""
    key = {"correction": "missed", "success": "liked"}.get(src)
    if key:
        try:
            capstats.bump(lid, key)
        except Exception as e:
            ctx.log(f"patchfirst: {key} not counted on {lid}: {e!r}")
        situtrace.fire(lid, f"{d['situation']} The assistant did: {d['did']}", same)


def _edit(d, src, raw, c, cid, wording, sids=None):
    """Queue the reword of lesson cid with this situation attached (status proposed, active only on his yes). The session's own
    words are recorded as for any repeat. A situation whose proposal was not queued is retired, never left proposed. `sids`: a list
    the stored situation's sid is added to."""
    occ = history.add(cid, src, raw, clean_text=c)
    sid = situations.add(cid, src, d["situation"], d["did"], d["disliked"], occ=occ, status=situations.PROPOSED)
    sids is None or sids.append(sid)
    try:
        pid = proposals.queue("edit", f"reword lesson {cid} to: {wording}", {"lesson_id": cid, "text": wording, "sids": [sid]})
    except BaseException:
        situations.retire(sid)
        raise
    if pid is None:
        situations.retire(sid)
        return f"The same change to the lesson {cid} is already proposed. Nothing to ask him now."
    return f"This repeats the lesson {cid}: queued as a proposal to reword it, with this situation attached. Nothing to ask him now."


def propose(d, src, raw, c, sids=None, paid=None):
    """Queue the proposal for a new lesson d (capwrite.write fields; c = its cleaned JSON); returns what to tell the session.
    `sids`: a list that gets the sid of the situation stored now (a reword proposal stores one; a new-lesson proposal none yet).
    `paid`: the marker of the write; a new-lesson proposal keeps its {tp, key} so his yes can link the situation it then creates."""
    try:
        same = compare(d["lesson"], d["situation"])
    except Exception as e:
        ctx.log(f"patchfirst: compare failed, treated as new: {e!r}")
        same = None
    bad = same and clean.violations(same[1], strict=True)  # the model's wording goes into a tracked file: the privacy scan first
    if bad:
        ctx.log(f"patchfirst: reworded lesson of {same[0]} failed the privacy scan, treated as new: {bad}")
        same = None
    if same:
        repeated(same[0], d, src)  # counted at once, whatever happens to the wording proposal
        return _edit(d, src, raw, c, *same, sids)
    slug = pending.slugify(d["slug"], pending.DEFAULT_SLUG)
    proposals.queue("new-lesson", f"add the lesson {slug}: {d['lesson']}", {
        "slug": slug, "lesson": d["lesson"], "situation": d["situation"], "did": d["did"], "disliked": d["disliked"],
        "his_words": raw, "source": src, **({"paid": {k: paid[k] for k in ("tp", "key")}} if paid else {})})
    return (f"Queued as a proposal; only his yes adds it, he answers in one line (yes / ignore). Do not ask him now. "
            f"Lesson: {d['lesson']}")
