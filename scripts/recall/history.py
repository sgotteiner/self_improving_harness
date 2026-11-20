"""Occurrence history: every repeat of a mistake, with the raw text, in a local SQLite file (gitignored).
cases/*.md keep only `occurrences: <count>` and `last_seen: <date>`. Each occurrence also gets a cleaned version
(clean.py: general wording, no names, paths or session ids) in column clean_text. The cleaned ones of approved cases go into the
store cases/situations.jsonl (situations.py, once per row id), and views.py generates cases/history/<case_id>.md from it (tracked,
feeds retrieval). Raw text and transcript paths never leave this database. Cleaning runs in a detached process after each record
(a brain call is too slow for the hook), and every later sync retries rows that failed and adds the cleaned rows the store lacks."""
import datetime, json, os, re, sqlite3, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ctx, index, situations, views

DB = os.path.join(HERE, "history.db")


def _con():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS occurrence(id INTEGER PRIMARY KEY, date TEXT, case_id TEXT, source TEXT, "
                "text TEXT, transcript TEXT)")
    if "clean_text" not in [r[1] for r in con.execute("PRAGMA table_info(occurrence)")]:
        con.execute("ALTER TABLE occurrence ADD COLUMN clean_text TEXT")
    return con


def add(case_id, source, text, transcript="", date=None, clean_text=None):
    """Returns the id of the new row. source: 'gate' (output gate block, text = its reason) or 'correction' (text = his words). clean_text: the session's own
    structured JSON, kept as is (no cleaning call)."""
    con = _con()
    occ = con.execute("INSERT INTO occurrence(date, case_id, source, text, transcript, clean_text) VALUES (?,?,?,?,?,?)",
                      (date or str(datetime.date.today()), case_id, source, text, transcript or "", clean_text)).lastrowid
    con.commit()
    con.close()
    return occ


def bump(path, date=None):
    """Set `occurrences` (+1) and `last_seen` in the case frontmatter."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"(---\r?\n)(.*?)(\r?\n---)", text, re.S)
    head = m.group(2)
    old = re.search(r"^occurrences:[ \t]*(\d+)[ \t]*$", head, re.M)
    n = int(old.group(1)) if old else 0
    head = re.sub(r"^occurrences:.*\n(?:  - .*\n?)*|^last_seen:.*\n?", "", head + "\n", flags=re.M).rstrip("\n")
    head += f"\noccurrences: {n + 1}\nlast_seen: {date or datetime.date.today()}"
    open(path, "w", encoding="utf-8", newline="").write(m.group(1) + head + m.group(3) + text[m.end():])


def record(path, source, text, transcript="", clean_text=None):
    cid = os.path.basename(path)[:-3]
    occ = add(cid, source, text, transcript, clean_text=clean_text)
    if clean_text:  # the session's own cleaned text goes into the store now; if that fails, sync adds the row by its id
        try:
            c = json.loads(clean_text)
            situations.add(cid, source, c["situation"], c["assistant_did"], c["disliked"], occ=occ)
        except Exception as e:
            ctx.log(f"history: situation not stored now, sync will add it: {e!r}")
    bump(path)
    spawn_sync()


def spawn_sync():
    """Clean and publish in a detached process; never raises (the raw row is already saved)."""
    try:
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
        subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "sync"], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)
    except Exception:
        pass


def _lesson(cid):
    """The general lesson of the case the occurrence belongs to (approved or still pending); '' if unknown."""
    for d in (index.CASES, os.path.join(index.CASES, "_pending")):
        p = os.path.join(d, cid + ".md")
        if os.path.exists(p):
            return index.parse(p).get("lesson", "")
    return ""


def backfill(con):
    """Add to the store every cleaned row of an approved lesson that it lacks. A row is there when its id (occ) is, or when an
    older line (from before ids were kept) has the same lesson, source, situation and did. Returns the number added."""
    ls, rows = views.lessons(), situations.read()
    have_occ = {r.get("occ") for r in rows}
    have = {(r["lesson_id"], r["source"], r["situation"], r["did"]) for r in rows}
    n = 0
    for i, date, cid, src, ct in con.execute("SELECT id, date, case_id, source, clean_text FROM occurrence WHERE clean_text LIKE '{%' ORDER BY id"):
        c = json.loads(ct)
        if cid in ls and i not in have_occ and (cid, src, c["situation"], c["assistant_did"]) not in have:
            n += situations.add(cid, src, c["situation"], c["assistant_did"], c["disliked"], date, occ=i) is not None
    return n


def sync(clean_new=True):
    """Clean every row without clean_text, add the cleaned rows of approved cases the store lacks, then rewrite the generated
    cases/history/<case>.md. Returns (cleaned, failed, files)."""
    import clean
    con = _con()
    done = failed = 0
    if clean_new:  # clean_text is JSON {situation, assistant_did, disliked}; older plain-sentence rows are redone
        todo = con.execute("SELECT id, case_id, source, text, transcript FROM occurrence WHERE clean_text IS NULL "
                           "OR clean_text NOT LIKE '{%' ORDER BY id").fetchall()
        for i, cid, src, text, tp in todo:
            c = clean.clean(text, src, _lesson(cid), tp)  # each lesson gets its own cleaning: his complaint is about that lesson
            if c:
                con.execute("UPDATE occurrence SET clean_text=? WHERE id=?", (json.dumps(c), i))
                con.commit()
                done += 1
            else:
                failed += 1
    try:
        backfill(con)
    except Exception as e:  # the next sync retries; the pages below still come from what the store has
        ctx.log(f"history: backfill failed: {e!r}")
        failed += 1
    con.close()
    ids = views.pages()  # the pages come from the store, not from history.db
    try:  # encode the new examples now, so the first search does not pay for them
        import embed
        embed.encode([t for cid in ids for t in index.history_texts(cid)])
    except Exception:
        failed += 1
    return done, failed, len(ids)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "sync":
    d, f, n = sync()
    print(f"cleaned {d}, failed {f}, history files {n}")
