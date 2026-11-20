"""The rules of cleanup.py, as plain functions of the data (no model call, nothing written). Every threshold is a named constant,
his to set. Counts are read since the lesson's last applied edit (baseline), so a reworded lesson is judged on its new wording."""
import datetime, hashlib, json

WRONG_MIN = 3        # gate blocks he judged wrong, at least this many and more than the right ones -> reword
MISSED_MIN = 3       # repeats he had to correct himself (the gate missed them) -> reword
NEWKIND_MIN = 2      # firings that matched none of the lesson's situations -> the lesson should widen -> reword
RETIRE_WEEKS = 4     # a situation with no hit this long (counted from its date or last hit) -> retire it
REVERT_MISSED = 2    # missed rising by this much ...
REVERT_DAYS = 28     # ... within this many days of an applied edit -> propose the old wording back
COOLDOWN_DAYS = 28   # a lesson that had a text proposal (any answer) this recently gets no new reword or merge
CLEANUP_DAYS = 7     # days between two cleanup runs ...
OVER_DAYS = 1        # ... and while the all-lessons text is over its size limit
RUN_STALE_MIN = 30   # a run that marked itself running this long ago is taken as crashed
NEWKIND_KEEP = 10    # notes of cases matching no situation kept per lesson (the oldest are dropped)
TEXT_KINDS = ("edit", "merge", "revert")
OPEN = ("queued", "offered", "shown")


def age(date, today):
    """Days from an ISO date to today; 0 for an empty or unreadable date (never old enough to act on)."""
    try:
        return (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(date)).days
    except (TypeError, ValueError):
        return 0


def lesson_set(ls):
    """A short fingerprint of the lessons (ids and texts): changes when one is added, removed or reworded."""
    return hashlib.sha1(json.dumps(sorted(ls.items()), ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def target(r):
    return r["data"]["into"] if r["kind"] == "merge" else r["data"].get("lesson_id")


def touched(r, sits):
    """The lesson ids a proposal concerns."""
    d = r["data"]
    ids = set(d.get("from", [])) | set(d.get("restore", [])) | {d[k] for k in ("lesson_id", "into") if d.get(k)}
    return ids | {s["lesson_id"] for s in sits if s["sid"] == d.get("sid")}


def busy(rows, sits):
    """Lessons with a proposal queued or open: they get no second one."""
    return set().union(*[touched(r, sits) for r in rows if r["status"] in OPEN])


def recent(rows, lid, today):
    return any(r["kind"] in TEXT_KINDS and r["status"] != "failed" and target(r) == lid and age(r["created"], today) < COOLDOWN_DAYS for r in rows)


def baseline(rows, lid):
    done = [r["data"]["stats_at"] for r in rows if r["status"] == "applied" and r["kind"] in TEXT_KINDS and target(r) == lid and "stats_at" in r["data"]]
    return done[-1] if done else {}


def reasons(lids, stats, rows, notes):
    """{lesson id: why it should be reworded} by the three reword rules."""
    out = {}
    for lid in lids:
        b, s = baseline(rows, lid), stats.get(lid, {})
        d = lambda k: s.get(k, 0) - b.get(k, 0)
        if d("wrong") >= WRONG_MIN and d("wrong") > d("right"):
            out[lid] = f"the gate was often wrong on it ({d('wrong')} false alarms, {d('right')} right)"
        elif d("missed") >= MISSED_MIN:
            out[lid] = f"the gate misreads it: {d('missed')} repeats were missed"
        elif len(notes.get(lid, [])) >= NEWKIND_MIN:
            out[lid] = "cases keep coming that match none of its situations"
    return out


def stale(sits, today):
    """Active situations with no hit for RETIRE_WEEKS since max(date, last_hit)."""
    return [s for s in sits if s["status"] == "active" and age(max(s["date"] or "", s["last_hit"] or ""), today) >= RETIRE_WEEKS * 7]


def dead(lids, sits, stats):
    """Lessons whose situations are all retired and that the gate never named (no right, wrong, ignored or missed)."""
    return [l for l in lids if (mine := [s for s in sits if s["lesson_id"] == l]) and all(s["status"] == "retired" for s in mine)
            and not any(stats.get(l, {}).values())]


def reverts(rows, stats, today):
    """[(applied proposal, lesson id)] of edits after which `missed` rose by REVERT_MISSED within REVERT_DAYS, not yet reverted."""
    out = []
    for r in rows:
        lid, d = target(r), r["data"]
        if (r["status"] == "applied" and r["kind"] in ("edit", "merge") and "stats_at" in d and age(d["applied"], today) <= REVERT_DAYS
                and stats.get(lid, {}).get("missed", 0) - d["stats_at"].get("missed", 0) >= REVERT_MISSED
                and not any(x["kind"] == "revert" and x["data"].get("of") == r["pid"] for x in rows)):
            out.append((r, lid))
    return out
