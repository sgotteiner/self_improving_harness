"""cases/stats.json: per lesson id how often he judged a gate block right or wrong, left it unanswered (ignored; capverdict.py),
or had to correct a repeat himself (missed; capwrite.py). One small file, no db; counting only, nothing else reads it. Written atomically."""
import json, os, time

import ctx, index, mdfile

KEYS = ("right", "wrong", "missed", "ignored")


def _locked(lock):
    """Take the lock file (retry ~3s; a lock older than 10s is a dead hook's and is broken)."""
    for _ in range(60):
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
            return True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > 10:
                    os.remove(lock)
            except OSError:
                pass
            time.sleep(0.05)
    return False


def bump(lesson_id, key):
    path = os.path.join(index.CASES, "stats.json")
    lock = path + ".lock"
    if not _locked(lock):
        ctx.log(f"capstats: locked, count skipped: {lesson_id} {key}")
        return
    try:
        try:
            s = json.loads(mdfile.read(path))
        except FileNotFoundError:
            s = {}
        except (OSError, ValueError) as e:  # never reset a file we cannot read: leave it and skip this count
            ctx.log(f"capstats: stats.json unreadable, left untouched, count skipped: {e!r}")
            return
        c = s.setdefault(lesson_id, {})
        for old in ("correct", "incorrect"):  # migration: the keys this file had before
            c.pop(old, None)
        for k in KEYS:
            c.setdefault(k, 0)
        c[key] += 1
        mdfile.write_atomic(path, json.dumps(s, indent=1, sort_keys=True))
    finally:
        os.remove(lock)
