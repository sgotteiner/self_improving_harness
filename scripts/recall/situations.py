"""The situations store: cases/situations.jsonl, one line per real situation behind a lesson (append-only). Everything else is
derived from it and the lesson files by views.py (history pages, LESSONS.md, the gate's all-lessons text). Only cleaned text lands
here (the raw words stay in history.db); a line from history.db keeps the id of its row (`occ`) and is never added twice. Existing
lines change only in status, hits, last_hit and lesson_id (a merge relinks), always under the store's lock. Stdlib only.
Usage: python -I scripts/recall/situations.py seed   (adds the hand-written `situation:` lines of the lessons)"""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import index, mdfile

FILE = index.STORE
SOURCES = ("correction", "gate", "work", "seed")
ACTIVE, RETIRED, PROPOSED = index.ACTIVE, "retired", "proposed"  # proposed: waits for his yes (proposals.py), then active or retired
SID_FORMAT = "s%04d"
EDITABLE = ("status", "hits", "last_hit", "lesson_id")


def path():
    return os.path.join(index.CASES, FILE)


def read():
    """Every line of the store, in order."""
    if not os.path.exists(path()):
        return []
    return [json.loads(l) for l in mdfile.read(path()).splitlines() if l.strip()]


def _put(rows):
    mdfile.write_atomic(path(), "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def _held():
    return mdfile.held(path() + ".lock")


def add(lesson_id, source, situation, did="", outcome="", date=None, occ=None, status=ACTIVE):
    """Append one line; returns its sid, or None when a line with this history.db row id (`occ`) is already there.
    The sid is counted inside the lock, so two writers never take the same one."""
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}")
    with _held() as got:
        if not got:
            raise OSError("situations store is locked")
        rows = read()
        if occ is not None and any(r.get("occ") == occ for r in rows):
            return None
        row = {"sid": SID_FORMAT % (len(rows) + 1), "lesson_id": lesson_id, "date": date or str(datetime.date.today()),
               "source": source, "occ": occ, "situation": situation, "did": did, "outcome": outcome, "status": status,
               "hits": 0, "last_hit": None}
        with open(path(), "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row["sid"]


def _edit(match, **changes):
    """Change the EDITABLE fields of every line where match(row) is true, in one locked read and rewrite; a value that is
    callable is called with the row. Returns the number of lines changed."""
    if not set(changes) <= set(EDITABLE):
        raise ValueError(f"only {EDITABLE} can change, not {sorted(changes)}")
    with _held() as got:
        if not got:
            raise OSError("situations store is locked")
        rows, n = read(), 0
        for r in rows:
            if match(r):
                r.update({k: v(r) if callable(v) else v for k, v in changes.items()})
                n += 1
        n and _put(rows)
        return n


def _one(sid, **changes):
    if not _edit(lambda r: r["sid"] == sid, **changes):
        raise KeyError(sid)


def retire(sid):
    _one(sid, status=RETIRED)


def activate(sid):
    _one(sid, status=ACTIVE)


def hit(sid, date=None):
    _one(sid, hits=lambda r: r["hits"] + 1, last_hit=date or str(datetime.date.today()))


def relink(old_ids, new_id):
    """A merge: every line of the lessons old_ids now belongs to new_id (one locked rewrite: all or none)."""
    return _edit(lambda r: r["lesson_id"] in old_ids, lesson_id=new_id)


def restore(moved):
    """Undo a merge's relink: {sid: lesson id it belonged to}."""
    return _edit(lambda r: r["sid"] in moved, lesson_id=lambda r: moved[r["sid"]])


def seed():
    """Add the hand-written `situation:` lines of every lesson the store lacks (a line already there, same lesson, source,
    situation, did, is not added twice). The lines of history.db come through history.py sync. Returns the number added."""
    have = {(r["lesson_id"], r["source"], r["situation"], r["did"]) for r in read()}
    n = 0
    for f in index.case_files():
        cid, d = os.path.basename(f)[:-3], index.parse(f)
        for s in d.get("situation", []):
            if (cid, "seed", s, "") not in have:
                add(cid, "seed", s, date=d.get("date", ""))
                have.add((cid, "seed", s, ""))
                n += 1
    return n


if __name__ == "__main__" and sys.argv[1:] == ["seed"]:
    print("added", seed(), "lines")
