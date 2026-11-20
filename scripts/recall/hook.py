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


def candidates(q):
    """[(score, case id, path or None)]: the graph's situation step when graph-recall is on, else the flat search."""
    if ctx.enabled("graph-recall"):
        import graph
        return graph.at_message(q, 8)
    import retrieve
    return [(s, c, None) for s, c in retrieve.search(q, 8, "emb")]


def recall_all(prompt, transcript):
    """Slot recall-all-lessons: one call, the situation and every lesson; the model names those that apply."""
    import alllessons as al, brain
    ls = al.lessons()
    out, _ = brain.ask(al.RECALL.format(ctx="\n".join(ctx.recent(transcript, 4)), prompt=prompt, lessons=al.block(ls)), tag="recall-all")
    return [f"Related past case (cases/{c}.md, {ls[c][0]}): {why} Lesson: {ls[c][1]} Right: {ls[c][2]}" for c, why in al.named(out, ls)]


def recall(prompt, transcript):
    if ctx.enabled("recall-all-lessons"):
        return recall_all(prompt, transcript)
    import brain, graph, index
    sit, _ = brain.ask(STEP1.format(ctx="\n".join(ctx.recent(transcript, 4)), prompt=prompt), tag="recall-1")
    hits = [h for h in candidates(ctx.chunks(sit + "\n" + prompt)) if h[0] >= ctx.RELEVANCE_MIN]
    if not hits:
        ctx.log("hook: no case above the relevance cutoff, no second brain call")
        return []
    metas = {c: index.meta(c) for _, c, _ in hits}
    paths = {c: p for _, c, p in hits}
    block = "\n".join(graph.case_line(c, m, paths[c]) for c, m in metas.items())
    out, _ = brain.ask(STEP2.format(sit=sit, cases=block), tag="recall-2")
    lines = []
    for l in out.splitlines()[:3]:
        cid, _, why = [x.strip(" -*`") for x in l.partition("|")]
        if cid in metas:
            date, _, lesson, right = metas[cid]
            path = f" {graph.trace(paths[cid])}" if paths[cid] else ""  # the traced path, graph-recall only
            lines.append(f"Related past case (cases/{cid}.md, {date}): {why}{path} Lesson: {lesson} Right: {right}")
    return lines


def stage(name, fn, default):
    """Run one stage; a failure is logged and never stops the others. Past the hook's time budget (ctx.BUDGET of its 300 s
    limit) brain.ask refuses each new call, so the stages that need it fail fast and the notes still print."""
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
    if ctx.enabled("delegation-hook"):  # first: the setup as it is at his message, before any slow stage; off until approved
        stage("delegation-snapshot", lambda: __import__("setupstate").save_snapshot(tp), None)
    kind_lines, drafted = [], None
    if ctx.enabled("delegation-hook"):  # one call: his kind of message; a correction (slot capture) makes the session write the case
        kind_lines = stage("delegation", lambda: __import__("delegate").input_step(prompt, tp)[0], [])
        drafted = next((l for l in kind_lines if l.startswith("Capture:")), None)
    # the day's proposal line (proposals.py shows none when the step that reads his yes, or capture, is off)
    stage("cleanup", lambda: __import__("cleanrun").start(), None)  # the lessons' upkeep: weekly or over the size limit, detached
    kind_lines += stage("proposal", lambda: [l for l in (__import__("proposals").line(tp),) if l], [])
    if ctx.enabled("decision-capture"):  # diary drafts: collected silently, like captured mistakes
        if drafted:  # the same message was a correction of his assistant, not a design decision
            ctx.log("hook: decision detection skipped, mistake capture asked the session to write a case")
        else:
            stage("decisions", lambda: __import__("decisions").process(prompt, tp), None)
    out = stage("vision", lambda: __import__("vision").lines(), [])  # VISION.md first, like a rule, on every human message
    if ctx.enabled("project-check"):  # first message of a session: the project's documents against the setup's rules
        out += stage("project-check", lambda: __import__("projcheck").first_message(tp, d.get("cwd", "")), [])
    out += kind_lines
    if ctx.enabled("recall-hook") and len(prompt.split()) >= 3:
        out += stage("recall", lambda: recall(prompt, tp), [])
    elif not out:
        ctx.log("hook: silent, recall off or prompt under 3 words")
    if ctx.enabled("flags-capture"):  # agents' own choices -> the project's flags file; last, it is the least urgent
        stage("flags", lambda: __import__("flags").process(tp), [])
    text = ""
    for line in out:
        if len(text) + len(line) + 1 > OUT_MAX:
            break
        text += line + "\n"
    if text:
        print(text.rstrip("\n"), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        ctx.log(f"hook: failed: {e!r}")
    sys.exit(0)
