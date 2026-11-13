"""Derived SQLite FTS5 index over cases/*.md. The markdown files stay the source of truth."""
import os, re, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.normpath(os.path.join(HERE, "..", "..", "cases"))
DB = os.path.join(HERE, "cases.db")
# bm25 column weights: id, situation, lesson, wrong, right (situation highest)
WEIGHTS = (2.0, 10.0, 3.0, 1.0, 1.0)
STOP = set("a an the to of in on at for and or but is are was be it its this that i me my we you do does did "
           "can could should would will just so as with from by if then than not no yes up out about into".split())


def parse(path):
    """Minimal parser for the case frontmatter: scalars, quoted scalars, '- ' lists."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    d, key = {}, None
    for line in (m.group(1) if m else "").splitlines():
        if line.startswith("  - ") and key:
            d[key].append(unq(line[4:]))
        elif ":" in line and not line.startswith(" "):
            key, val = line.split(":", 1)
            val = val.strip()
            d[key] = unq(val) if val else []
    return d


def unq(s):
    s = s.strip()
    return s[1:-1] if len(s) > 1 and s[0] == s[-1] and s[0] in "\"'" else s


def case_files():
    return [os.path.join(CASES, f) for f in sorted(os.listdir(CASES)) if f.endswith(".md") and f != "README.md"]


def stale():
    if not os.path.exists(DB):
        return True
    t = os.path.getmtime(DB)
    return any(os.path.getmtime(f) > t for f in case_files()) or os.path.getmtime(__file__) > t


def build():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("CREATE VIRTUAL TABLE cases USING fts5(id, situation, lesson, wrong, \"right\", "
                "tokenize='porter unicode61')")
    con.execute("CREATE TABLE meta(id TEXT PRIMARY KEY, date TEXT, situation TEXT, lesson TEXT, \"right\" TEXT)")
    for f in case_files():
        d = parse(f)
        cid = d.get("id") or os.path.basename(f)[:-3]
        sit = d.get("situation", [])
        con.execute("INSERT INTO cases VALUES (?,?,?,?,?)",
                    (cid.replace("-", " ") + " " + os.path.basename(f), " ".join(sit),
                     d.get("lesson", ""), d.get("wrong", ""), d.get("right", "")))
        con.execute("INSERT INTO meta VALUES (?,?,?,?,?)",
                    (cid, d.get("date", ""), sit[0] if sit else "", d.get("lesson", ""), d.get("right", "")))
    con.commit()
    con.close()


def search(query, k=3):
    """Return [(score, id)] best first; score = -bm25 (higher is better). Rebuilds if stale."""
    if stale():
        build()
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOP and len(w) > 1]
    if not words:
        return []
    q = " OR ".join('"%s"' % w for w in dict.fromkeys(words))
    con = sqlite3.connect(DB)
    w = ",".join(str(x) for x in WEIGHTS)
    rows = con.execute(f"SELECT id, bm25(cases, {w}) FROM cases WHERE cases MATCH ? ORDER BY 2 LIMIT ?", (q, k)).fetchall()
    con.close()
    return [(-s, cid.split(" ")[-1][:-3] if cid.endswith(".md") else cid) for cid, s in rows]


def meta(cid):
    con = sqlite3.connect(DB)
    r = con.execute("SELECT date, situation, lesson, \"right\" FROM meta WHERE id=?", (cid,)).fetchone()
    con.close()
    return r


if __name__ == "__main__":
    build()
    print("built", DB, len(case_files()), "cases")
