"""When two proposals are the same change, and when a dropped (or failed) one may come back (used by proposals.queue). A reword,
revert or new lesson is keyed on its lesson alone (the wording is model-written and differs every time) and stays blocked
DROP_DAYS after the drop, unless a new real occurrence is attached to the new proposal: a situation stored after the old one was
queued (an edit), or a new case in his own words (a new lesson). A merge is keyed on its lesson set, any other kind on its data;
those stay blocked for good. Fails open (a broken check blocks nothing). Stdlib only."""
import datetime, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

DAY = 86400
DROP_DAYS = 30
LESSON_KINDS = ("edit", "revert", "new-lesson")
OWN_SOURCES = ("correction", "success", "gate")  # the cases whose his_words are his own message (capwrite.OWN_WORDS and gate)


def key(kind, data):
    try:
        if kind == "merge":
            return kind, sorted([data["into"], *data["from"]])
        if kind == "new-lesson":
            return kind, data["slug"]
        if kind in ("edit", "revert"):
            return kind, data["lesson_id"]
    except (KeyError, TypeError):
        pass
    return kind, data


def sits():
    """How many situations are stored now: a situation with a higher number was stored after this moment."""
    try:
        import situations
        return len(situations.read())
    except Exception as e:
        ctx.log(f"proposals: situations not counted: {e!r}")
        return None


def _fresh(old, data):
    """Does the new proposal carry a real occurrence that the dropped `old` did not?"""
    if data.get("sids"):  # an edit: its situation was stored for it just before it was queued
        return old.get("sits") is not None and any(s and int(s[1:]) > old["sits"] for s in data["sids"])
    return data.get("source") in OWN_SOURCES and data.get("his_words") != old["data"].get("his_words")


def blocks(old, kind, data, now):
    """Is the dropped or failed proposal `old` a reason to skip the new one of the same key?"""
    try:
        if kind not in LESSON_KINDS:
            return True
        closed = old.get("at") or datetime.datetime.fromisoformat(old["created"]).timestamp()
        return now - closed < DROP_DAYS * DAY and not _fresh(old, data)
    except Exception as e:
        ctx.log(f"proposals: drop check failed, not blocking: {e!r}")
        return False
