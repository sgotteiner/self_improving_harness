"""Adding to a markdown file the safe way: line endings kept, the new text placed under its section, the file written
through a temp file and replaced (never half written), and what was already there never edited."""
import contextlib, os, re, tempfile, threading, time

LOCK_TRIES, LOCK_WAIT, LOCK_STALE = 60, 0.05, 10  # ~3 s of retries; a lock file older than 10 s is a dead hook's and is broken
BOUNDARY = re.compile(r"^(?:---+[ \t]*\r?$|#{1,2} )", re.M)  # where a section ends: a rule or the next # / ## heading


def read(path):
    return open(path, encoding="utf-8", newline="").read()


def write_atomic(path, text):
    """Temp file next to the target, then os.replace; the target keeps its line endings because nothing is translated."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.path.exists(tmp) and os.remove(tmp)
        raise


def _break_stale(lock):
    """Rename the lock to a name of our own (atomic: of several waiters one wins), then judge the file we got; a fresh lock
    that was taken between the check and the rename is linked back."""
    dead = f"{lock}.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}.dead"
    os.rename(lock, dead)
    if time.time() - os.path.getmtime(dead) <= LOCK_STALE:
        with contextlib.suppress(OSError):
            os.link(dead, lock)
    os.remove(dead)


def locked(lock):
    """Take the lock file `lock` (retries, breaks a stale one); False when it stayed taken."""
    for _ in range(LOCK_TRIES):
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
            return True
        except (FileExistsError, PermissionError):  # Windows: a lock file being deleted answers PermissionError, not "exists"
            try:
                if time.time() - os.path.getmtime(lock) > LOCK_STALE:
                    _break_stale(lock)
            except OSError:
                pass
            time.sleep(LOCK_WAIT)
    return False


@contextlib.contextmanager
def held(lock):
    """`with held(lock) as got:` -> got is False when the lock could not be taken; a taken lock is always released
    (one a waiter already broke as stale is gone: not an error)."""
    got = locked(lock)
    try:
        yield got
    finally:
        if got:
            with contextlib.suppress(FileNotFoundError):
                os.remove(lock)


def insert_under(text, heading, block, new_before=None, rule=False):
    """`text` with `block` (lines joined by \\n) added after the last line of the section whose heading line is
    `heading`. A missing section is created: before the first line matching `new_before`, else at the end of the file
    (after a `---` rule when `rule`).
    Everything already in the text stays byte for byte; the file's own line ending (\\r\\n or \\n) is used."""
    nl = "\r\n" if "\r\n" in text else "\n"
    block = block.strip("\n").replace("\n", nl)
    m = re.search(r"^" + re.escape(heading) + r"[ \t]*\r?$", text, re.M)
    if not m:
        sect = f"{heading}{nl}{nl}{block}{nl}"
        n = re.search(new_before, text, re.M) if new_before else None
        if n:
            return text[:n.start()] + sect + nl + text[n.start():]
        return text + ("" if text.endswith("\n") or not text else nl) + nl + "---" + nl + nl + sect
    b = BOUNDARY.search(text, m.end())
    end = len(text[:b.start() if b else len(text)].rstrip())  # after the section's last non-blank text
    return text[:end] + nl + nl + block + (text[end:] or nl)


def inferred_why(text):
    """True when a **Why:** line of a diary holds '(inferred)' as a marker. The word quoted in an Idea or elsewhere does not count."""
    return any("(inferred)" in l for l in text.splitlines() if l.lstrip().startswith("**Why:**"))
