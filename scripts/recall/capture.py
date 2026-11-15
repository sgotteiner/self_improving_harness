"""Mistake capture. (a) the owner corrects the assistant -> the brain drafts a case into cases/_pending/ (or, if it
closely matches an existing case, records an occurrence there); (b) the output gate caught a known mistake ->
occurrence on that case. Pending cases are not used by the hooks until moved to cases/ by the owner's approval."""
import datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, ctx, embed, history, index, validate

PENDING = os.path.join(index.CASES, "_pending")
TODO = os.path.join(ctx.ROOT, "tasks", "todo.md")
# cosine of the draft to an existing case above which it counts as the same mistake. Measured by eval_recall.py:
# the best different-case/unrelated score is 0.76, so 0.77 is the floor for no wrong merge; 0.80 keeps a margin. A wrong
# merge hides a new lesson inside another case; a missed merge only leaves a duplicate pending case to discard.
SAME = 0.80
DETECT = ("The assistant's previous turn:\n{prev}\n\nTool calls: {tools}{rej}\n\nThe owner's new message: {prompt}\n\n"
          "Is the new message a correction or complaint about how the assistant behaved (not what it built): e.g. 'I told "
          "you', 'that's not what I asked', 'why did you', ignoring an instruction, missing the point? A new request, an "
          "approval or a thanks is NO. Reply 'NO' or 'YES | <one sentence: the assistant's mistake>'.")
DRAFT = ("Draft a lesson case from this mistake of an AI coding assistant. Mistake: {why}\nAssistant's turn:\n{prev}\n"
         "Owner's words: {prompt}\n\nReply with JSON only: {{\"slug\": \"kebab-case-id\", \"situation\": [3-4 phrasings of how "
         "the situation shows up, including what the session is doing at that moment], \"wrong\": \"what was done wrong\", "
         "\"right\": \"what to do instead\", \"lesson\": \"one sentence, a GENERAL principle that would apply in other "
         "situations too, not tied to this case's details (he rejects case-specific lessons); if the correction is only "
         "an instruction for this task (a format, a fix), say so in the lesson instead of inventing a principle\", "
         "\"replay\": \"a prompt that recreates the "
         "situation in a fresh session\", \"pass_if\": [2-3 checkable signals]}}. No personal data.")


def _json(s):
    m = re.search(r"\{.*\}", s, re.S)
    return json.loads(m.group(0)) if m else None


def _docs():
    out = {}
    for d, tag in ((index.CASES, ""), (PENDING, "_pending/")):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".md") and f != "README.md":
                c = index.parse(os.path.join(d, f))
                out[tag + f[:-3]] = c.get("situation", []) + [c.get("lesson", "")] 
    return out


def from_gate(cid, why, tp):
    history.record(os.path.join(index.CASES, cid + ".md"), "gate", why, tp)


def process(prompt, tp):
    """Called on a new human prompt. Returns the path touched, or None."""
    prev, tools = ctx.last_turn(tp, prompt.strip())
    if not prev.strip():
        return None
    rej = "\nA tool call was rejected or interrupted by the owner this turn." if ctx.rejected_tool(tp, prompt.strip()) else ""
    out, _ = brain.ask(DETECT.format(prev=prev, tools="; ".join(tools) or "none", rej=rej, prompt=prompt),
                       tag="capture-detect")
    if not out.upper().startswith("YES"):
        return None
    why = out.partition("|")[2].strip()
    d = _json(brain.ask(DRAFT.format(why=why, prev=prev, prompt=prompt), tag="capture-draft")[0])
    if not d or not d.get("situation"):
        return None
    sc = embed.scores(" ".join(d["situation"]) + " " + d.get("lesson", ""), _docs())
    best = max(sc, key=sc.get) if sc else None
    if best and sc[best] >= SAME:
        path = os.path.join(PENDING if best.startswith("_pending/") else index.CASES, best.split("/")[-1] + ".md")
        history.record(path, "correction", prompt.strip(), tp)
        return path
    slug = re.sub(r"[^a-z0-9-]+", "-", d.get("slug", "captured-mistake").lower()).strip("-")[:60] or "captured-mistake"
    path = os.path.join(PENDING, slug + ".md")
    os.makedirs(PENDING, exist_ok=True)
    q = lambda s: '"' + str(s).replace('"', "'").replace("\n", " ") + '"'
    body = (f"---\nid: {slug}\ndate: {datetime.date.today()}\nsource: captured automatically; transcript {tp}\nstatus: pending\n"
            f"asked: false\nlevel: advice\nhis_words: {q(prompt.strip())}\nsituation:\n"
            + "".join(f"  - {q(x)}\n" for x in d["situation"])
            + f"wrong: {q(d.get('wrong', ''))}\nright: {q(d.get('right', ''))}\nlesson: {q(d.get('lesson', ''))}\n"
            f"replay: {q(d.get('replay', ''))}\npass_if:\n" + "".join(f"  - {q(x)}\n" for x in d.get("pass_if", []))
            + "occurrences: 0\n---\n")
    open(path, "w", encoding="utf-8").write(body)
    history.record(path, "correction", prompt.strip(), tp)  # his words go to history.db; the count becomes 1
    try:
        _todo(slug)
    except OSError as e:
        ctx.log(f"capture: todo not updated: {e!r}")
    return path


def _todo(slug):
    lines = open(TODO, encoding="utf-8").read().split("\n") if os.path.exists(TODO) else []
    i = lines.index("Done") if "Done" in lines else len(lines)
    lines.insert(i, f"- [ ] review captured case `{slug}` (cases/_pending/{slug}.md): add, edit or discard")
    open(TODO, "w", encoding="utf-8").write("\n".join(lines))


def move(slug, level="advice"):
    """Move a pending case into cases/ with its level; drop source/his_words/status/asked (the words stay in history.db)."""
    src = os.path.join(PENDING, slug + ".md")
    dst = os.path.join(index.CASES, slug + ".md")
    if not os.path.exists(src):
        raise FileNotFoundError(f"no pending case {src}")
    if os.path.exists(dst):
        raise FileExistsError(f"{dst} already exists")
    if level not in validate.LEVELS:
        raise ValueError(f"level {level!r} is not one of {validate.LEVELS}")
    t = open(src, encoding="utf-8").read()
    t = re.sub(r"^(source|his_words|status|asked):.*\n", "", t, flags=re.M)
    t = re.sub(r"^level:.*$", "level: " + level, t, count=1, flags=re.M)
    open(dst, "w", encoding="utf-8", newline="").write(t)
    os.remove(src)
    return dst


def approve(slug, level="advice"):
    """Save a lesson as one complete step, in the order cases/README.md requires; every step is reported and a failed
    step is a failed approve (returns False). Steps: move, index, history (clean + publish occurrences),
    embeddings (encoded now, not at the first search), then the checks of validate.py (fields, privacy,
    occurrences, embeddings, recall rank). Examples are the written fields and the real cleaned occurrences, nothing
    generated. The case file stays in cases/ even when a step fails, so it can be fixed."""
    rep = []

    def step(name, fn):
        try:
            ok, ev = fn()
        except Exception as ex:
            ok, ev = False, f"error {ex!r}"
        rep.append((name, ok, ev))
        return ok

    dst = [None]

    def do_move():
        dst[0] = move(slug, level)
        return True, f"cases/{slug}.md, level {level}"

    def do_index():
        index.build()
        return index.meta(slug) is not None, f"{len(index.case_files())} cases indexed"

    def do_history():
        done, failed, files = history.sync()
        return failed == 0, f"{done} occurrences cleaned now, {failed} failed, {len(index.history_texts(slug))} for this case"

    def do_embed():
        d = index.parse(dst[0])
        t = validate.texts(d)
        embed.encode(t)
        return embed.missing(t) == 0, f"{len(t)} texts encoded and cached"

    if step("move", do_move):
        for name, fn in (("index", do_index), ("history", do_history), ("embeddings", do_embed)):
            if not step(name, fn):
                break
        else:
            rep += validate.run(dst[0], only=("fields", "privacy", "occurrences", "recall"))
    return _print(f"approve {slug} ({level})", rep)


def check_all(only=None):
    """Run the validation over every case in cases/ (or just `only`, with the evidence of every check).
    Returns True when all pass."""
    ok = True
    for f in index.case_files():
        if only and os.path.basename(f)[:-3] != only:
            continue
        ok &= _print(os.path.basename(f)[:-3], validate.run(f), quiet=not only)
    print("check:", "all cases pass" if ok else "FAILED")
    return bool(ok)


def _print(title, rep, quiet=False):
    allok = all(r[1] for r in rep)
    if not quiet or not allok:
        print(title + (": ok" if allok else ": FAILED"))
        for name, ok, ev in rep:
            if not quiet or not ok:
                print(f"  [{'ok' if ok else 'FAIL'}] {name}: {ev}")
    else:
        print(f"{title}: ok ({', '.join(n for n, _, _ in rep)})")
    return allok


def ask_notes():
    """[(path, note)] for each pending case not yet asked about. Injected by the next UserPromptSubmit, which calls
    mark_asked(path) only after the note was printed."""
    out = []
    for f in sorted(os.listdir(PENDING)) if os.path.isdir(PENDING) else []:
        p = os.path.join(PENDING, f)
        d = index.parse(p) if f.endswith(".md") else {}
        if d.get("asked") == "false":
            sit = d.get("situation") or [""]
            sit = sit[0] if isinstance(sit, list) else sit
            # His format (2026-11-14): "where is the situation, what you did, what I didn't like and how I told you
            # to be better, which is the lesson" - the bare lesson alone can't be judged.
            out.append((p, f"Captured a possible mistake (cases/_pending/{f}). Present it to the owner in plain words as: "
                           "1) the situation, 2) what you did, 3) what he didn't like, 4) how he told you to do better, "
                           f"quoting him, 5) the lesson. Draft: situation: {sit} | what you did: {d.get('wrong', '')} | "
                           f"his words: {d.get('his_words', '')} | better: {d.get('right', '')} | lesson: "
                           f"{d.get('lesson', '')}. Then ask the owner: add it to "
                           "the knowledge? and how: as a lesson brought in when the situation repeats (level: advice), as a "
                           "check before finishing (level: check), or as a hard rule (level: rule); or edit or discard. Apply "
                           f"his answer: `python -I scripts/recall/capture.py approve {f[:-3]} <advice|check|rule>` (one step: moves it, indexes, embeds, checks, prints a report; read the report back to him "
                           "to cases/, keeps his words only in history.db), or edit it, or delete the file."))
    return out


def mark_asked(path):
    t = open(path, encoding="utf-8").read().replace("asked: false", "asked: true", 1)
    open(path, "w", encoding="utf-8", newline="").write(t)


if __name__ == "__main__" and len(sys.argv) >= 2:
    if sys.argv[1] == "approve" and len(sys.argv) >= 3:
        sys.exit(0 if approve(*sys.argv[2:4]) else 1)
    if sys.argv[1] == "check":
        sys.exit(0 if check_all(*sys.argv[2:3]) else 1)
    print("usage: capture.py approve <slug> <advice|check|rule> | capture.py check [slug]")
    sys.exit(2)
