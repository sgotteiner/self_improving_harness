"""Occurrence history: every repeat of a mistake, with full text, in a local SQLite file (gitignored).
cases/*.md keep only `occurrences: <count>` and `last_seen: <date>`; no text, paths or session ids."""
import datetime, os, re, sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def add(case_id, source, text, transcript="", date=None):
    """source: 'gate' (output gate block, text = its reason) or 'correction' (text = his words)."""
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS occurrence(id INTEGER PRIMARY KEY, date TEXT, case_id TEXT, source TEXT, "
                "text TEXT, transcript TEXT)")
    con.execute("INSERT INTO occurrence(date, case_id, source, text, transcript) VALUES (?,?,?,?,?)",
                (date or str(datetime.date.today()), case_id, source, text, transcript or ""))
    con.commit()
    con.close()


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


def record(path, source, text, transcript=""):
    add(os.path.basename(path)[:-3], source, text, transcript)
    bump(path)
