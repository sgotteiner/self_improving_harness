"""What a proposal does when he says yes (apply) or not (drop). Kinds and their data:
  new-lesson        {slug, lesson, situation, did, disliked, his_words, source, sids?}  -> a lesson file via casesave.approve
  edit | revert     {lesson_id, text, sids?}                       -> the lesson's wording is replaced (revert: the earlier wording)
  merge             {into, from: [ids], text, sids?}               -> `into` gets `text`, the others' situations are relinked, they are archived
  retire-situation  {sid}                                          -> the situation is retired
  retire-lesson     {lesson_id}                                    -> the lesson is archived
`sids` = situations (status proposed) that wait with the proposal: his yes makes them active, anything else (a failed apply too)
retires them. A merge is all or nothing: a failure puts every lesson file and its stats back.
Nothing is deleted: an archived lesson moves to cases/_archive/ with its stats (<id>.stats.json), retired situations stay in the store."""
import datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstats, clean, ctx, index, mdfile, pending, situations, views

KINDS = ("new-lesson", "edit", "merge", "retire-situation", "retire-lesson", "revert")
ARCHIVE_DIR = "_archive"
NEW_LEVEL = "advice"  # the level of a lesson added by a proposal (casesave.approve)
LESSON_LINE = re.compile(r"^lesson:[^\r\n]*", re.M)


def _file(cid):
    return os.path.join(index.CASES, cid + ".md")


def _set_lesson(cid, text):
    """The lesson line of cases/<cid>.md replaced; the text goes into a tracked file, so the privacy scan has the last word."""
    bad = clean.violations(text, strict=True)
    if bad:
        raise ValueError(f"privacy scan hit in the new wording of {cid}: {bad}")
    new, n = LESSON_LINE.subn(lambda _: "lesson: " + pending.q(text), mdfile.read(_file(cid)), count=1)
    if not n:
        raise ValueError(f"{cid} has no lesson line")
    mdfile.write_atomic(_file(cid), new)


def _archive(cid):
    """cases/<id>.md -> cases/_archive/<id>.md, its stats beside it as <id>.stats.json; returns the stats (for _unarchive)."""
    out = os.path.join(index.CASES, ARCHIVE_DIR)
    os.makedirs(out, exist_ok=True)
    stats = capstats.take(cid)
    try:
        mdfile.write_atomic(os.path.join(out, cid + ".stats.json"), json.dumps(stats, indent=1, sort_keys=True))
        os.replace(_file(cid), os.path.join(out, cid + ".md"))
    except BaseException:
        capstats.put(cid, stats)
        raise
    return stats


def _unarchive(cid, stats):
    out = os.path.join(index.CASES, ARCHIVE_DIR)
    os.replace(os.path.join(out, cid + ".md"), _file(cid))
    os.remove(os.path.join(out, cid + ".stats.json"))
    capstats.put(cid, stats)


def _merge(d):
    into, frm = d["into"], list(d["from"])
    if into in frm:
        raise ValueError("a lesson cannot be merged into itself")
    saved = mdfile.read(_file(into))
    for cid in frm:
        mdfile.read(_file(cid))  # a missing lesson stops here, before anything changed
    done = []
    try:
        _set_lesson(into, d["text"])
        for cid in frm:
            done.append((cid, _archive(cid)))
        situations.relink(frm, into)
    except BaseException:
        for cid, stats in reversed(done):
            _unarchive(cid, stats)
        mdfile.write_atomic(_file(into), saved)
        raise


def _new(d):
    import casesave, history
    path = os.path.join(casesave.PENDING, d["slug"] + ".md")
    os.makedirs(casesave.PENDING, exist_ok=True)
    mdfile.write_atomic(path, pending.case_text(d["slug"], d, d["his_words"], datetime.date.today()))
    history.record(path, d["source"], d["his_words"], clean_text=json.dumps(
        {"situation": d["situation"], "assistant_did": d["did"], "disliked": d["disliked"]}))
    if not casesave.approve(d["slug"], NEW_LEVEL):
        raise RuntimeError(f"approve of {d['slug']} failed")


def apply(r):
    k, d = r["kind"], r["data"]
    if k == "new-lesson":
        _new(d)
    elif k in ("edit", "revert"):
        _set_lesson(d["lesson_id"], d["text"])
    elif k == "merge":
        _merge(d)
    elif k == "retire-situation":
        situations.retire(d["sid"])
    elif k == "retire-lesson":
        _archive(d["lesson_id"])
    else:
        raise ValueError(f"unknown proposal kind {k!r}")
    for sid in d.get("sids", []):
        situations.activate(sid)
    try:
        views.build()
    except Exception as e:  # the views are derived and rebuilt by the next build: the change itself is done
        ctx.log(f"propapply: views not rebuilt: {e!r}")


def drop(r):
    for sid in r["data"].get("sids", []):
        situations.retire(sid)
