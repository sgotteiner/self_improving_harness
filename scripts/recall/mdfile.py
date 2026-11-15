"""Adding to a markdown file the safe way: line endings kept, the new text placed under its section, the file written
through a temp file and replaced (never half written), and what was already there never edited."""
import os, re, tempfile

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
