"""Evals only (eval_mechanism.py): rebuild the assistant turn of each real occurrence from history.db (raw text + transcript
path) and the transcript, and pick turns that have no occurrence. A turn is a transcript cut just before the entry where the
owner corrected (his message) or the gate blocked (the Stop-hook feedback entry), written to a temp file so ctx.last_turn
and the gate read it exactly as they read a live transcript."""
import json, os, random, sqlite3, tempfile
import ctx, history, index

OUT = tempfile.mkdtemp(prefix="mech-")


def _cut(es, text, source):
    """Index of the entry where this occurrence happened, else None."""
    key = " ".join(text.split())[:40]
    for n, e in enumerate(es):
        if e["type"] != "user":
            continue
        t = " ".join(" ".join(b.get("text", "") for b in ctx.blocks(e) if b.get("type") == "text").split())
        if key in t and (t.startswith("Stop hook feedback") if source == "gate" else ctx.is_human(t)):
            return n
    return None


def _write(es, n, name):
    p = os.path.join(OUT, name + ".jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(e) + "\n" for e in es[:n])
    return p


def occurrence_turns():
    """[{cid, i, key, source, tp (cut transcript) or None, why (reason it is unavailable), cut, orig}], one per published
    occurrence, in the order of cases/history/<case>.md (which is the order of history.db rows with a clean_text)."""
    con = sqlite3.connect(history.DB)
    out, cache = [], {}
    for f in index.case_files():
        cid = os.path.basename(f)[:-3]
        rows = con.execute("SELECT source, text, transcript FROM occurrence WHERE case_id=? AND clean_text LIKE '{%' ORDER BY id", (cid,)).fetchall()
        for i, r in enumerate(index.history_records(cid)):
            o = dict(cid=cid, i=i, key=index.occ_key(r), source=r["source"], tp=None, why="", cut=None, orig=None, text="")
            out.append(o)
            if i >= len(rows):
                o["why"] = "no history.db row"
                continue
            src, text, orig = rows[i]
            o["orig"], o["text"] = orig, text
            if not orig or not os.path.exists(orig):
                o["why"] = "transcript missing"
                continue
            es = cache.setdefault(orig, ctx.entries(orig))
            n = _cut(es, text, src)
            if n is None:
                o["why"] = "occurrence not found in the transcript (file changed since)"
            elif not ctx.last_turn(_write(es, n, f"{cid}-{i}"))[0].strip():
                o["why"] = "no assistant text in that turn"
            else:
                o["tp"], o["cut"] = os.path.join(OUT, f"{cid}-{i}.jsonl"), n
    return out


def clean_turns(occ, n=20, seed=7):
    """n turns, drawn with a fixed seed from the transcripts of the occurrences, that hold no occurrence: not a turn a
    correction or a gate block (of any case, pending ones too) ended in, with assistant text and tool calls. [{name, tp}]."""
    es_of, cuts = {}, {}
    for orig, src, text in sqlite3.connect(history.DB).execute("SELECT transcript, source, text FROM occurrence"):
        if orig and os.path.exists(orig):
            es = es_of.setdefault(orig, ctx.entries(orig))
            cuts.setdefault(orig, set()).add(_cut(es, text, src))
    pool = []
    for orig, es in sorted(es_of.items()):
        hs = [k for k, e in enumerate(es) if ctx.human_text(e)]
        for a, b in zip(hs, hs[1:]):  # the last human message's turn may still be running
            if b not in cuts[orig] and not any(a < c < b for c in cuts[orig] if c is not None):
                pool.append((orig, b))
    random.Random(seed).shuffle(pool)
    out = []
    for orig, b in pool:
        p = _write(es_of[orig], b, f"clean-{len(out)}")
        txt, tools = ctx.last_turn(p)
        if len(txt) >= 150 and tools:
            out.append(dict(name=f"clean-{len(out)}", tp=p))
        if len(out) == n:
            break
    return out
