"""UserPromptSubmit hook. Brain 1 describes the situation, retrieval picks ~8 cases, brain 2 keeps the 0-3 that
apply. Also: asks about freshly captured pending cases once, and runs mistake capture. Never blocks; error -> exit 0."""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, capture, ctx, index, retrieve

MIN_SCORE = 0.60  # below this no candidate is worth a second brain call (negatives top out near 0.68)
STEP1 = ("Describe in 1-2 sentences what is going on right now in this coding session and what the owner wants or "
         "what the assistant is about to do. Facts only.\n\n{ctx}\n\nOwner's new message: {prompt}")
STEP2 = ("Situation: {sit}\n\nPast cases (lessons from earlier mistakes):\n{cases}\n\nWhich of these cases (0 to 3) clearly apply "
         "to this situation, so that repeating the old mistake is a real risk? Be strict: when unsure, none. Reply with "
         "'NONE' or one line per case: <id> | <why it applies, one factual sentence>.")


def recall(prompt, transcript):
    sit, _ = brain.ask(STEP1.format(ctx="\n".join(ctx.recent(transcript, 4)), prompt=prompt[:1500]), tag="recall-1")
    hits = retrieve.search(sit + "\n" + prompt[:500], 8, "emb", True)
    hits = [(s, c) for s, c in hits if s >= MIN_SCORE]
    if not hits:
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


def main():
    if ctx.skip_env("RECALL_HOOK"):
        return
    d = json.load(sys.stdin)
    prompt, tp = d.get("prompt", ""), d.get("transcript_path", "")
    if not ctx.is_human(prompt):
        return
    out = capture.ask_notes() if ctx.enabled("capture") else []
    if ctx.enabled("capture"):
        capture.process(prompt, tp)  # drafted now, asked at the next prompt
    if ctx.enabled("recall-hook") and len(prompt.split()) >= 3:
        out += recall(prompt, tp)
    text = "\n".join(out)
    if text:
        print(text[:2500])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
