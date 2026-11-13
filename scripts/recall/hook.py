"""UserPromptSubmit hook. Brain 1 describes the situation, retrieval picks ~8 cases, brain 2 keeps the 0-3 that
apply. Also: asks about freshly captured pending cases once, and runs mistake capture. Never blocks; error -> exit 0."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx  # stdlib only; the other modules need numpy, fastembed, so each stage imports them itself

OUT_MAX = 9000  # platform limit: hook output over 10,000 chars is cut by Claude Code; whole lines are dropped to stay under
STEP1 = ("Describe in 1-2 sentences what is going on right now in this coding session and what the owner wants or "
         "what the assistant is about to do. Facts only.\n\n{ctx}\n\nOwner's new message: {prompt}")
STEP2 = ("Situation: {sit}\n\nPast cases (lessons from earlier mistakes):\n{cases}\n\nWhich of these cases (0 to 3) clearly apply "
         "to this situation, so that repeating the old mistake is a real risk? Be strict: when unsure, none. Reply with "
         "'NONE' or one line per case: <id> | <why it applies, one factual sentence>.")


def recall(prompt, transcript):
    import brain, index, retrieve
    sit, _ = brain.ask(STEP1.format(ctx="\n".join(ctx.recent(transcript, 4)), prompt=prompt), tag="recall-1")
    hits = retrieve.search(ctx.chunks(sit + "\n" + prompt), 8, "emb", True)
    hits = [(s, c) for s, c in hits if s >= ctx.RELEVANCE_MIN]
    if not hits:
        ctx.log("hook: no case above the relevance cutoff, no second brain call")
        return []
    metas = {c: index.meta(c) for _, c in hits}
    block = "\n".join(f"- {c}: situation: {m[1]} Lesson: {m[2]} Right: {m[3]}" for c, m in metas.items())
    out, _ = brain.ask(STEP2.format(sit=sit, cases=block), tag="recall-2")
    lines = []
    for l in out.splitlines()[:3]:
        cid, _, why = [x.strip(" -*`") for x in l.partition("|")]
        if cid in metas:
            date, _, lesson, right = metas[cid]
            lines.append(f"Related past case (cases/{cid}.md, {date}): {why} Lesson: {lesson} Right: {right}")
    return lines


def stage(name, fn, default):
    """Run one stage; a failure is logged and never stops the others."""
    try:
        return fn()
    except Exception as e:
        ctx.log(f"hook: {name} failed: {e!r}")
        return default


def main():
    if ctx.skip_env("RECALL_HOOK"):
        ctx.log("hook: silent, brain call or RECALL_HOOK=0")
        return
    d = json.load(sys.stdin)
    prompt, tp = d.get("prompt", ""), d.get("transcript_path", "")
    if not ctx.is_human(prompt):
        ctx.log("hook: silent, not a human prompt")
        return
    cap = ctx.enabled("capture")
    notes = stage("ask-notes", lambda: __import__("capture").ask_notes(), []) if cap else []
    if cap:  # drafted now, asked at the next prompt
        stage("capture", lambda: __import__("capture").process(prompt, tp), None)
    out = [n for _, n in notes]
    if ctx.enabled("recall-hook") and len(prompt.split()) >= 3:
        out += stage("recall", lambda: recall(prompt, tp), [])
    elif not out:
        ctx.log("hook: silent, recall off or prompt under 3 words")
    text, shown = "", 0
    for line in out:
        if len(text) + len(line) + 1 > OUT_MAX:
            break
        text += line + "\n"
        shown += 1
    if text:
        print(text.rstrip("\n"), flush=True)
    for p, _ in notes[:shown]:  # marked asked only after the note was printed
        stage("mark-asked", lambda: __import__("capture").mark_asked(p), None)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        ctx.log(f"hook: failed: {e!r}")
    sys.exit(0)
