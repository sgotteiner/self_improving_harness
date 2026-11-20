"""State of the work review (workreview.py): results/work_review.json, {transcript: {entries, humans, occ, props}, running, again}, and
the marks taken at the moment a stretch is cut. Stdlib only."""
import json, os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, history, mdfile, proposals

STATE = os.path.join(ctx.ROOT, "scripts", "recall", "results", "work_review.json")


def path():
    return os.environ.get("RECALL_WORK_STATE") or STATE  # the tests point it at a temp file


def read():
    try:
        return json.loads(mdfile.read(path()))
    except (OSError, ValueError):
        return {}


def change(fn):
    """Let fn(state) change the state under the lock and write it back; returns fn's value."""
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    with mdfile.held(path() + ".lock") as got:
        if not got:
            raise OSError("work-review state is locked")
        s = read()
        out = fn(s)
        mdfile.write_atomic(path(), json.dumps(s, indent=1, sort_keys=True))
        return out


def humans(es):
    return sum(1 for e in es if ctx.human_text(e))


def last_occ():
    """Highest row id of history.db (0 if none): capture's occurrences all land there."""
    try:
        con = sqlite3.connect(history.DB)
        try:
            return con.execute("SELECT MAX(id) FROM occurrence").fetchone()[0] or 0
        finally:
            con.close()
    except sqlite3.Error:
        return 0


def cut(tp, es):
    """The marks of the moment a stretch is cut (taken before the brain call): entries and human turns so far, the last
    history.db row id, the number of queued proposals."""
    return {"entries": len(es), "humans": humans(es), "occ": last_occ(), "props": len(proposals.read())}


def captured(prev, now):
    """True when capture recorded an occurrence or queued a proposal since the marks `prev` (its own work rows and work proposals
    do not count). Without earlier marks nothing is known: False."""
    if "occ" not in prev:
        return False
    try:
        con = sqlite3.connect(history.DB)
        try:
            n = con.execute("SELECT COUNT(*) FROM occurrence WHERE id > ? AND id <= ? AND source != 'work'", (prev["occ"], now["occ"])).fetchone()[0]
        finally:
            con.close()
    except sqlite3.Error:
        n = 0
    new = proposals.read()[prev.get("props", len(proposals.read())):now["props"]]
    return bool(n or any(r["data"].get("source") != "work" for r in new))
