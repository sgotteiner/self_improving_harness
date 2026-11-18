"""Evals only (pathmech.py): the parts of the owner's path mechanism. A path = situation -> did -> complaint -> lesson, each its own
node with its own embedding (embed.encode); several paths may lead to one lesson. Message stage: the live situation vs SITUATION
nodes only. Reply stage: the assistant's turn vs the DID nodes of the candidate paths only. Decision: the brain gets the turn and
the matched paths (situation, did, his complaint, lesson). Paths are in results/paths_v2.jsonl (gitignored: raw context)."""
import json, os, sqlite3
import numpy as np
import brain, ctx, embed, history, mechturns

PATHS = os.path.join(ctx.ROOT, "scripts", "recall", "results", "paths_v2.jsonl")
CUT, N = ctx.RELEVANCE_MIN, 3  # the shared relevance cutoff; candidates = top N above it
RENDER = ("The last turns of a session between an owner and his AI assistant; the last line is the owner's newest message:\n{turns}\n\n"
          "Write ONE situation in exactly this form, on one line, in plain words, only what the turns say. A part the turns do not "
          "state is '(not stated)'; never guess.\nWorking on: <what is being worked on> Just done: <what the assistant had just done> "
          "State: <the state it is in now> He asked: <what the owner asks in his newest message, and the situation that made him ask>\n"
          "Reply with that one line only.")
JUDGE = ("Past mistakes of this assistant, each with what the assistant did then and what the owner did not like about it.\n"
         "{paths}\n\nThe assistant's latest turn.\nTool calls this turn:\n{tools}\n\nFinal message:\n{text}\n\n"
         "Compare only this turn's actions and claims with what the assistant did in each path and what he did not like. Does this "
         "turn repeat what he disliked in one of them (the same kind of action or claim, which he would dislike for the same reason)? "
         "Reply 'NONE' or '<path id> | <one sentence: what is repeated>'.")


def ask(prompt, tag):
    err = None
    for _ in range(2):  # a transient failure of the cheap model is retried once
        try:
            return brain.ask(prompt, tag=tag)[0]
        except Exception as e:
            err = e
    ctx.log(f"pathmech: {tag} failed twice: {err!r}")
    return "!error"


def render(tp):
    """The situation, in the one template, written by the brain from the last 4 turns + his newest message of this transcript."""
    return " ".join(ask(RENDER.format(turns="\n".join(ctx.recent(tp, 5))), "render").split())


def turn_of(tp):
    """(text, tool lines) of the latest turn, and the transcript cut after his message that began it (the live message stage)."""
    es = ctx.entries(tp)
    m = max(k for k, e in enumerate(es) if ctx.human_text(e))
    return ctx.last_turn(tp), mechturns._write(es, m + 1, os.path.basename(tp)[:-6] + "-msg")


def load():
    """[path dicts] with the cut transcript of the mistake turn (tp) and the one up to his message (tp_msg)."""
    con = sqlite3.connect(history.DB)
    out = []
    for l in open(PATHS, encoding="utf-8"):
        p = json.loads(l)
        raw = con.execute("SELECT text FROM occurrence WHERE id=?", (p["occ"],)).fetchone()[0]
        es = ctx.entries(p["transcript"])
        n = mechturns._cut(es, p.get("cut_text") or raw, p["source"] if not p.get("cut_text") else "correction")
        p["tp"] = mechturns._write(es, n, f"path-{p['occ']}")
        (p["text"], p["tools"]), p["tp_msg"] = turn_of(p["tp"])
        p["raw"] = raw
        out.append(p)
    return out


def nodes(paths, lessons):
    """Embed every node of its own: {occ: {kind: vec}} for situation (his-written), did, complaint; {lesson id: vec}."""
    ks = ("situation", "did", "complaint")
    v = embed.encode([p[k] for p in paths for k in ks] + list(lessons.values()))
    g = {p["occ"]: {k: v[3 * i + j] for j, k in enumerate(ks)} for i, p in enumerate(paths)}
    return g, dict(zip(lessons, v[3 * len(paths):]))


def at_message(live, sit, exclude):
    """The live situation vs SITUATION nodes only: [(cosine, occ)] top N above the cutoff. sit = {occ: vec}; exclude = held-out occ."""
    q = embed.encode([live])[0]
    s = sorted(((float(v @ q), o) for o, v in sit.items() if o != exclude), reverse=True)
    return [x for x in s[:N] if x[0] >= CUT]


def judge(text, tools, cands, by_occ):
    """ONE brain call, no embedding: this turn's actions and claims vs the candidate paths' did + his complaint (the situation only
    picked the candidates). Returns (lesson id of the path repeated | None | '!error', raw answer)."""
    if not cands:
        return None, ""
    block = "\n".join(f"- path {o}. What the assistant did: {by_occ[o]['did']} What he did not like (his words): "
                      f"{by_occ[o]['complaint']} Lesson: {by_occ[o]['lesson']}" for _, o in cands)
    out = ask(JUDGE.format(paths=block, tools="\n".join(tools) or "(none)", text=text), "pathjudge")
    if out == "!error":
        return "!error", out
    pid, _, why = [x.strip(" *`") for x in out.partition("|")]
    hit = next((by_occ[o]["lesson"] for _, o in cands if pid.replace("path", "").strip() == str(o)), None)
    return (hit if why else None), out
