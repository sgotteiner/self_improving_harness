"""Graph memory over the cases, built at load from the .md files (the files stay the storage). Behind the slot graph-recall.
A case is a LESSON node. Each block of cases/history/<case>.md is a PATH: situation -> what the assistant did -> what he
did not like -> the lesson; the same block in several cases' history is one path leading to all of those lessons (several
mistakes -> one lesson, one mistake -> several lessons). The case's own fields are one more path (situation lines -> wrong;
a pending draft also has his words as the complaint). Every node has its own embedding (cached by embed.py).
Search matches the step: at_message = his message vs situation nodes; at_reply = the assistant's plan/results vs
what-it-did nodes (and each path as a whole). A lesson scores as its best node; the path of that node is returned. A lesson keeps its own text.
The data holds only disliked paths (every stored path ends in a complaint or the case's own wrong action)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, embed, graphscore, index

VARIANT = "best"  # lesson scoring (graphscore.agg); eval_variants.py sets it to try the others
REPLY_KINDS = ("action", "path")  # ("action",) drops the whole-path nodes
ATTACH = "all"  # capture: all | single | agree (match below)
_G = {}  # {with pending: data}, built once per process; reset() drops it (tests, evals that change the files)


def reset():
    _G.clear()


def _list(v):
    return v if isinstance(v, list) else ([v] if v else [])


def _load(pending=False):
    """{lessons {id: {lesson, right, date}}, paths {key: path}, nodes [{kind, text, lessons, path, vec}]}. Pending drafts
    (id '_pending/<slug>') are lessons too when asked for, so a new mistake can be compared with them."""
    if pending in _G:
        return _G[pending]
    cases = [(os.path.basename(f)[:-3], f) for f in index.case_files()]
    pd = os.path.join(index.CASES, "_pending")
    if pending and os.path.isdir(pd):
        cases += [("_pending/" + f[:-3], os.path.join(pd, f)) for f in sorted(os.listdir(pd)) if f.endswith(".md") and f != "README.md"]
    lessons, paths = {}, {}
    for lid, f in cases:
        d = index.parse(f)
        lessons[lid] = dict(lesson=d.get("lesson", ""), right=d.get("right", ""), date=d.get("date", ""))
        paths[("own", lid)] = dict(key=("own", lid), lessons=[lid], sit=_list(d.get("situation")), did=d.get("wrong"),
                                   complaint=d.get("his_words"), date=d.get("date", ""))
        for r in [] if lid.startswith("_pending/") else index.history_records(lid):
            p = paths.setdefault(index.occ_key(r), dict(key=index.occ_key(r), lessons=[], sit=_list(r.get("situation")),
                                                        did=r.get("assistant did"), complaint=r.get("he did not like"), date=r["date"]))
            p["lessons"].append(lid)
    nodes = [dict(kind="lesson", text=v["lesson"], lessons=[lid], path=None) for lid, v in lessons.items()]
    for p in paths.values():
        nodes += [dict(kind=k, text=t, lessons=p["lessons"], path=p["key"])
                  for k, ts in (("situation", p["sit"]), ("action", _list(p["did"])), ("complaint", _list(p["complaint"]))) for t in ts]
    for p in paths.values():  # the whole disliked path as one text (the flat history document): a long turn matches it better than a part
        if p["key"][0] != "own":
            nodes.append(dict(kind="path", text=index.joined({"situation": p["sit"][0], "assistant did": p["did"], "he did not like": p["complaint"]}), lessons=p["lessons"], path=p["key"]))
    nodes = [n for n in nodes if n["text"]]
    for n, v in zip(nodes, embed.encode([n["text"] for n in nodes])):
        n["vec"] = v
    _G[pending] = dict(lessons=lessons, paths=paths, nodes=nodes)
    return _G[pending]


def lesson(lid, pending=False):
    """{lesson, right, date} of a lesson node: its own text."""
    return _load(pending)["lessons"][lid]


def occurrences():
    """The real occurrence paths (cases/history blocks): [{key, lessons, sit, did, complaint, date}]."""
    return [p for k, p in _load()["paths"].items() if k[0] != "own"]


def _best(kinds, query, k, exclude, pending=False, variant=None):
    """[(score, lesson id, path)]: per lesson its score from the nodes of these kinds (graphscore.agg), with the path of its best
    node (None for a lesson node)."""
    g = _load(pending)
    nodes = [n for n in g["nodes"] if n["kind"] in kinds and n["path"] not in exclude]
    if not nodes:
        return []
    sim = (np.stack([n["vec"] for n in nodes]) @ embed.encode([query] if isinstance(query, str) else list(query)).T).max(axis=1)
    rows = [(float(v), lid, n["path"]) for n, v in zip(nodes, sim) for lid in n["lessons"] if lid not in exclude]  # exclude: path keys and lesson ids
    return [(s, lid, g["paths"].get(p)) for s, lid, p in graphscore.agg(rows, variant or VARIANT)][:k]


def at_message(query, k=3, exclude=()):
    """His message / the situation vs SITUATION nodes only -> [(score, lesson id, path)]. exclude = path keys (or lesson ids) held out."""
    return _best(("situation",), query, k, exclude)


def at_reply(query, k=3, exclude=()):
    """The assistant's plan/results vs WHAT-IT-DID nodes and whole-path nodes -> same return. A whole turn is long: against the
    short action parts alone only 6 of 16 real turns found their lesson, with the whole path as well 13 (eval, round 2)."""
    return _best(REPLY_KINDS, query, k, exclude)


def any_node(query, k=3, exclude=()):
    """The best node of any kind per lesson (validate.py's rank check)."""
    return _best(("situation", "action", "complaint", "lesson"), query, k, exclude)


def match(parts, exclude=()):
    """Capture: parts = {kind: text} of a new mistake (lesson, action, complaint). Lessons (pending drafts too) whose node of that
    kind scores >= ctx.SAME -> [(score, lesson id)] best first. ATTACH: all = every one; single = only the best; agree = only
    those that reach SAME on two kinds."""
    out, kinds = {}, {}
    for kind, text in parts.items():
        for s, lid, _ in _best((kind,), text, 999, exclude, pending=True, variant="best"):
            out[lid] = max(out.get(lid, 0), s)
            kinds[lid] = kinds.get(lid, 0) + (s >= ctx.SAME)
    hits = sorted(((s, c) for c, s in out.items() if s >= ctx.SAME), reverse=True)
    return hits[:1] if ATTACH == "single" else [h for h in hits if kinds[h[1]] >= 2] if ATTACH == "agree" else hits


def trace(p):
    """The traced path as words for the brain and the injected line: past situation / what was done / what he did not like."""
    if not p:
        return ""
    parts = (("situation", p["sit"][0] if p["sit"] else None), ("what was done", p["did"]), ("he did not like", p["complaint"]))
    return "Past: " + "; ".join(f"{k}: {v}" for k, v in parts if v) + "."


def case_line(cid, meta, p):
    """One case for a brain prompt (index.meta row). No path = the flat line, unchanged; a path = its trace."""
    return f"- {cid}: " + (trace(p) if p else f"situation: {meta[1]}") + f" Lesson: {meta[2]} Right: {meta[3]}"
