"""cases/stats.json: per lesson id how often he judged a gate block right or wrong, left it unanswered (ignored; capverdict.py),
or had to correct a repeat himself (missed; capwrite.py); an archived lesson's counts leave with it (take). One small file, no db; counting only, nothing else reads it. Written atomically."""
import json, os

import ctx, index, mdfile

KEYS = ("right", "wrong", "missed", "ignored")


def _modify(change, what):
    """Run change(stats dict) under the file lock and write the result atomically; returns its value (None when skipped)."""
    path = os.path.join(index.CASES, "stats.json")
    with mdfile.held(path + ".lock") as got:
        if not got:
            ctx.log(f"capstats: locked, skipped: {what}")
            return None
        try:
            s = json.loads(mdfile.read(path))
        except FileNotFoundError:
            s = {}
        except (OSError, ValueError) as e:  # never reset a file we cannot read: leave it and skip this change
            ctx.log(f"capstats: stats.json unreadable, left untouched, skipped: {what}: {e!r}")
            return None
        out = change(s)
        mdfile.write_atomic(path, json.dumps(s, indent=1, sort_keys=True))
        return out


def bump(lesson_id, key):
    def change(s):
        c = s.setdefault(lesson_id, {})
        for old in ("correct", "incorrect"):  # migration: the keys this file had before
            c.pop(old, None)
        for k in KEYS:
            c.setdefault(k, 0)
        c[key] += 1
    _modify(change, f"count {lesson_id} {key}")


def get(lesson_id=None):
    """The counts of one lesson (all four keys), or of every lesson {id: counts} when none is given. Read only."""
    try:
        s = json.loads(mdfile.read(os.path.join(index.CASES, "stats.json")))
    except FileNotFoundError:
        s = {}
    full = lambda c: {k: c.get(k, 0) for k in KEYS}
    return full(s.get(lesson_id, {})) if lesson_id else {k: full(v) for k, v in s.items()}


def take(lesson_id):
    """Remove a lesson's counts from stats.json and return them ({} when it had none): an archived lesson keeps them with it."""
    return _modify(lambda s: s.pop(lesson_id, {}), f"take {lesson_id}") or {}


def put(lesson_id, counts):
    """Give a lesson its counts back (undoes take when an archive fails)."""
    if counts:
        _modify(lambda s: s.__setitem__(lesson_id, counts), f"put {lesson_id}")


def move(lesson_id, src, dst, n):
    """Move n counts of one lesson from key src to key dst (his verdict on blocks that were counted ignored); never below 0."""
    def change(s):
        c = {k: s.get(lesson_id, {}).get(k, 0) for k in KEYS}
        n_ = min(n, c[src])
        c[src] -= n_
        c[dst] += n_
        s[lesson_id] = c
    _modify(change, f"move {lesson_id} {src}->{dst}")
