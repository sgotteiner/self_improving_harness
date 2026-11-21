"""Derived SQLite FTS5 index over cases/*.md. The markdown files stay the source of truth."""
import json, os, re, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.normpath(os.path.join(HERE, "..", "..", "cases"))
DB = os.path.join(HERE, "cases.db")
# bm25 column weights: id, situation, lesson, wrong, right (situation highest)
WEIGHTS = (2.0, 10.0, 3.0, 1.0, 1.0)
NOT_LESSONS = ("README.md", "LESSONS.md")  # files of cases/ that are not lesson files (LESSONS.md is generated)
STORE, ACTIVE = "situations.jsonl", "active"  # the situations store (situations.py) and the status of a live line
PAGE_SOURCES = ("correction", "gate", "work", "reflect", "success")  # a seed line is a hand-written situation: no did / outcome, so no history block
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


PARTS = ("situation", "assistant did", "he did not like", "lesson")  # the parts of one occurrence, in file order


OUTCOME = PARTS[2]  # the one slot every source stores its outcome in; the key stays, only the words shown depend on the source
OUTCOME_LABELS = {"success": "he liked", "work": "what came of it", "reflect": "what came of it"}  # the other sources are complaints: PARTS' own label


def label(part, source):
    """The words shown for a part of an occurrence: the outcome reads as what he liked, or what came of it, by its source."""
    return OUTCOME_LABELS.get(source, part) if part == OUTCOME else part


def history_records(cid):
    """Cleaned occurrences of a lesson, read from the store (cases/situations.jsonl), active ones in store order:
    [{"date", "source", <PARTS>}]; the lesson part is the lesson's current text."""
    p, d = os.path.join(CASES, STORE), os.path.join(CASES, cid + ".md")
    if not os.path.exists(p):
        return []
    lesson = parse(d).get("lesson", "") if os.path.exists(d) else ""
    rows = [json.loads(l) for l in open(p, encoding="utf-8").read().splitlines() if l.strip()]
    return [{"date": r["date"], "source": r["source"], **dict(zip(PARTS, (r["situation"], r["did"], r["outcome"], lesson)))}
            for r in rows if r["lesson_id"] == cid and r["status"] == ACTIVE and r["source"] in PAGE_SOURCES]


def block(r):
    """The history-page block of one occurrence record (history_records' shape): the one place that format lives."""
    return f"## {r['date']} | {r['source']}\n" + "".join(f"- {label(k, r['source'])}: {r[k]}\n" for k in PARTS)


def occ_key(r):
    """Identity of an occurrence block (the lesson line is the case's own): one block in several cases' history is one path."""
    return tuple(r.get(k) for k in ("date", "source") + PARTS[:3])


def joined(r):
    """One recall document of an occurrence: its situation, what the assistant did, what he did not like."""
    return " ".join(f"{label(k, r.get('source')).capitalize()}: {r[k]}" for k in PARTS[:3] if r.get(k))


def history_texts(cid, skip=()):
    """One recall document per real occurrence: its situation, what the assistant did, what he did not like. The
    lesson is not repeated (the case's own lesson is a document of its own). skip = occ_keys left out (held-out evals)."""
    return [joined(r) for r in history_records(cid) if occ_key(r) not in skip]


def case_files():
    return [os.path.join(CASES, f) for f in sorted(os.listdir(CASES)) if f.endswith(".md") and f not in NOT_LESSONS]


def stale():
    if not os.path.exists(DB):
        return True
    t = os.path.getmtime(DB)
    if any(os.path.getmtime(f) > t for f in case_files()) or os.path.getmtime(__file__) > t:
        return True
    # A case moved in (approve keeps its old mtime) or deleted changes the set of ids without a newer mtime.
    con = sqlite3.connect(DB)
    try:
        ids = {r[0] for r in con.execute("SELECT id FROM meta")}
    except sqlite3.Error:
        return True
    finally:
        con.close()
    return ids != {os.path.basename(f)[:-3] for f in case_files()}


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
    q = "{id situation lesson wrong right} : (" + q + ")"
    con = sqlite3.connect(DB)
    w = ",".join(str(x) for x in WEIGHTS)
    rows = con.execute(f"SELECT id, bm25(cases, {w}) FROM cases WHERE cases MATCH ? ORDER BY 2 LIMIT ?", (q, k)).fetchall()
    con.close()
    return [(-s, cid.split(" ")[-1][:-3] if cid.endswith(".md") else cid) for cid, s in rows]


def meta(cid):
    if stale():  # the embedding path never calls search(), so meta() must keep the table current itself
        build()
    con = sqlite3.connect(DB)
    r = con.execute("SELECT date, situation, lesson, \"right\" FROM meta WHERE id=?", (cid,)).fetchone()
    con.close()
    return r


if __name__ == "__main__":
    build()
    print("built", DB, len(case_files()), "cases")
