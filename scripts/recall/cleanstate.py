"""Small local state of the lessons' upkeep: cases/_pending/cleanup.json (never pushed). {"last_run": <date>, "newkind": {lesson_id:
[case text, ...]}}: the cases that fired a lesson but matched none of its situations (situtrace.py, the last R.NEWKIND_KEEP per
lesson), evidence the lesson should widen; cleanup.py reads them for its reword rule and clears them once a reword is queued.
Also the run's bookkeeping: running (when a run started), last_run (the day of the last successful run), last_fail (the day of a
crashed one: retried the next day), merge_none (fingerprint of the lessons the merge call last found nothing to merge in). Written atomically under a lock."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cleanrules as R, index, mdfile


def path():
    return os.path.join(index.CASES, "_pending", "cleanup.json")


def read():
    try:
        return json.loads(mdfile.read(path()))
    except FileNotFoundError:
        return {}


def change(fn):
    """Let fn(state) change the state under the lock and write it back; returns fn's value."""
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    with mdfile.held(path() + ".lock") as got:
        if not got:
            raise OSError("cleanup state is locked")
        s = read()
        out = fn(s)
        mdfile.write_atomic(path(), json.dumps(s, indent=1, sort_keys=True))
        return out


def note_new(lesson_id, case):
    def add(s):
        notes = s.setdefault("newkind", {}).setdefault(lesson_id, [])
        notes.append(case)
        del notes[:-R.NEWKIND_KEEP]
    change(add)
