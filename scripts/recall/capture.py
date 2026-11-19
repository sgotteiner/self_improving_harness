"""Mistake capture. The detection is the CORRECTION kind of delegate.input_step (one call per message); the session writes the case with
`capture.py write` (capwrite.py) into cases/_pending/, or an occurrence on an existing lesson (also what the output gate asks
for when it caught a known mistake). Pending cases are not used by the hooks until moved to cases/ by the owner's approval."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capwrite, ctx, embed, index, pending
from casesave import PENDING, approve, check_all, move  # noqa: F401 (the CLI below; callers of capture.move/approve)

# DRAFT and matches() are no longer on the capture path
DRAFT = ("Draft a lesson case from this mistake of an AI coding assistant. Mistake: {why}\nAssistant's turn:\n{prev}\n"
         "Owner's words: {prompt}\n\nReply with JSON only: {{\"slug\": \"kebab-case-id\", \"situation\": [3-4 phrasings of how "
         "the situation shows up, including what the session is doing at that moment], \"wrong\": \"what was done wrong\", "
         "\"right\": \"what to do instead\", \"lesson\": \"one sentence, a GENERAL principle that would apply in other "
         "situations too, not tied to this case's details (he rejects case-specific lessons); if the correction is only "
         "an instruction for this task (a format, a fix), say so in the lesson instead of inventing a principle\", "
         "\"replay\": \"a prompt that recreates the "
         "situation in a fresh session\", \"pass_if\": [2-3 checkable signals]}}. No personal data.")


def _docs():
    out = {}
    for d, tag in ((index.CASES, ""), (PENDING, "_pending/")):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".md") and f != "README.md":
                c = index.parse(os.path.join(d, f))
                out[tag + f[:-3]] = c.get("situation", []) + [c.get("lesson", "")] 
    return out


def graph_matches(d, why, exclude=()):
    """The graph's capture compare: his lesson against lesson nodes, what was done against action nodes, his complaint against
    complaint nodes; the lessons graph.match returns (graph.ATTACH decides how many)."""
    import graph
    parts = {"lesson": d.get("lesson", ""), "action": d.get("wrong", ""), "complaint": why}
    return [c for _, c in graph.match({k: v for k, v in parts.items() if v}, set(exclude))]


def matches(d, why, exclude=()):
    """Case ids (pending ones as '_pending/<slug>') that a new mistake repeats; [] = it is new. exclude = ids left out (evals).
    Off: the single best case by situation + lesson. On (graph-recall): graph_matches."""
    if ctx.enabled("graph-recall"):
        return graph_matches(d, why, exclude)
    sc = {c: s for c, s in embed.scores(" ".join(d["situation"]) + " " + d.get("lesson", ""), _docs()).items() if c not in exclude}
    best = max(sc, key=sc.get) if sc else None
    return [best] if best and sc[best] >= ctx.SAME else []


def _note(f, d):
    sit = d.get("situation") or [""]
    sit = sit[0] if isinstance(sit, list) else sit
    # His format (2026-11-14): "where is the situation, what you did, what I didn't like and how I told you
    # to be better, which is the lesson" - the bare lesson alone can't be judged.
    return (f"Captured a possible mistake (cases/_pending/{f}.md). Present it to the owner in plain words as: "
            "1) the situation, 2) what you did, 3) what he didn't like, 4) how he told you to do better, "
            f"quoting him, 5) the lesson. Draft: situation: {sit} | what you did: {d.get('wrong', '')} | "
            f"his words: {d.get('his_words', '')} | better: {d.get('right', '')} | lesson: "
            f"{d.get('lesson', '')}. Then ask the owner: add it to "
            "the knowledge? and how: as a lesson brought in when the situation repeats (level: advice), as a "
            "check before finishing (level: check), or as a hard rule (level: rule); or edit or discard. Apply "
            f"his answer: `python -I scripts/recall/capture.py approve {f} <advice|check|rule>` (one step: moves it, indexes, embeds, checks, prints a report; read the report back to him "
            "to cases/, keeps his words only in history.db), or edit it, or delete the file.")


def ask_notes(unasked_only=True):
    """[(path, question)] for the pending cases; `drafts.py show` lists them all when he asks to review the drafts."""
    return pending.ask_notes(PENDING, _note, unasked_only)


if __name__ == "__main__" and len(sys.argv) >= 2:
    if sys.argv[1] == "approve" and len(sys.argv) >= 3:
        sys.exit(0 if approve(*sys.argv[2:4]) else 1)
    if sys.argv[1] == "check":
        sys.exit(0 if check_all(*sys.argv[2:3]) else 1)
    if sys.argv[1] == "lessons":
        print(*[f"{i}: {l}" for i, l in capwrite.lessons()], sep="\n")
        sys.exit(0)
    if sys.argv[1] == "write" and len(sys.argv) >= 4 and sys.argv[2] == "--none":
        ok, msg = capwrite.none(sys.argv[3], "gate" if "--gate" in sys.argv[4:] else "correction")
        print(msg, file=sys.stdout if ok else sys.stderr)
        sys.exit(0 if ok else 1)
    if sys.argv[1] == "write" and len(sys.argv) >= 3:
        try:
            ok, msg = capwrite.write(json.load(open(sys.argv[2], encoding="utf-8")))
        except (OSError, ValueError) as e:
            ok, msg = False, f"cannot read the JSON file: {e}"
        print(msg, file=sys.stdout if ok else sys.stderr)
        sys.exit(0 if ok else 1)
    print("usage: capture.py approve <slug> <advice|check|rule> | capture.py check [slug] | capture.py write <json file> | capture.py write --none '<why>' [--gate] | capture.py lessons")
    sys.exit(2)
