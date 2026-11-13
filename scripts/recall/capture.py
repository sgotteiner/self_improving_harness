"""Mistake capture. (a) the owner corrects the assistant -> the brain drafts a case into cases/_pending/ (or, if it
closely matches an existing case, records an occurrence there); (b) the output gate caught a known mistake ->
occurrence on that case. Pending cases are not used by the hooks until moved to cases/ by the owner's approval."""
import datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, ctx, embed, index

PENDING = os.path.join(index.CASES, "_pending")
TODO = os.path.join(ctx.ROOT, "tasks", "todo.md")
SAME = 0.80  # cosine of the draft to an existing case above which it counts as the same mistake
DETECT = ("The assistant's previous turn:\n{prev}\n\nTool calls: {tools}{rej}\n\nThe owner's new message: {prompt}\n\n"
          "Is the new message a correction or complaint about how the assistant behaved (not what it built): e.g. 'I told "
          "you', 'that's not what I asked', 'why did you', ignoring an instruction, missing the point? A new request, an "
          "approval or a thanks is NO. Reply 'NO' or 'YES | <one sentence: the assistant's mistake>'.")
DRAFT = ("Draft a lesson case from this mistake of an AI coding assistant. Mistake: {why}\nAssistant's turn:\n{prev}\n"
         "Owner's words: {prompt}\n\nReply with JSON only: {{\"slug\": \"kebab-case-id\", \"situation\": [3-4 phrasings of how "
         "the situation shows up, including what the session is doing at that moment], \"wrong\": \"what was done wrong\", "
         "\"right\": \"what to do instead\", \"lesson\": \"one sentence\", \"replay\": \"a prompt that recreates the "
         "situation in a fresh session\", \"pass_if\": [2-3 checkable signals]}}. No personal data.")


def _json(s):
    m = re.search(r"\{.*\}", s, re.S)
    return json.loads(m.group(0)) if m else None


def add_occurrence(path, line):
    """Append a line to the `occurrences:` list in the frontmatter (creating it); the count is its length."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"(---\r?\n)(.*?)(\r?\n---)", text, re.S)
    head, item = m.group(2), '  - "' + line.replace('"', "'").replace("\n", " ")[:300] + '"'
    if re.search(r"^occurrences:\s*$", head, re.M):
        head = re.sub(r"(^occurrences:\s*\n(?:  - .*\n?)*)", lambda g: g.group(1).rstrip("\n") + "\n" + item + "\n",
                      head + "\n", flags=re.M).rstrip("\n")
    else:
        head += "\noccurrences:\n" + item
    open(path, "w", encoding="utf-8", newline="").write(m.group(1) + head + m.group(3) + text[m.end():])


def _docs():
    out = {}
    for d, tag in ((index.CASES, ""), (PENDING, "_pending/")):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".md") and f != "README.md":
                c = index.parse(os.path.join(d, f))
                out[tag + f[:-3]] = c.get("situation", []) + [c.get("lesson", "")] + c.get("enriched", [])
    return out


def _stamp(tp):
    return f"{datetime.date.today()} {os.path.basename(tp or 'no-transcript')}"


def from_gate(cid, why, tp):
    add_occurrence(os.path.join(index.CASES, cid + ".md"), f"{_stamp(tp)}: output gate blocked: {why}")


def process(prompt, tp):
    """Called on a new human prompt. Returns the path touched, or None."""
    prev, tools = ctx.last_turn(tp, prompt.strip())
    if not prev.strip():
        return None
    rej = "\nA tool call was rejected or interrupted by the owner this turn." if ctx.rejected_tool(tp, prompt.strip()) else ""
    out, _ = brain.ask(DETECT.format(prev=prev[:2500], tools="; ".join(tools[-8:]) or "none", rej=rej, prompt=prompt[:1500]),
                       tag="capture-detect")
    if not out.upper().startswith("YES"):
        return None
    why = out.partition("|")[2].strip()
    d = _json(brain.ask(DRAFT.format(why=why, prev=prev[:2500], prompt=prompt[:1500]), tag="capture-draft")[0])
    if not d or not d.get("situation"):
        return None
    sc = embed.scores(" ".join(d["situation"][:2]) + " " + d.get("lesson", ""), _docs())
    best = max(sc, key=sc.get)
    line = f"{_stamp(tp)}: owner said: {prompt.strip()[:200]}"
    if sc[best] >= SAME:
        path = os.path.join(PENDING if best.startswith("_pending/") else index.CASES, best.split("/")[-1] + ".md")
        add_occurrence(path, line)
        return path
    slug = re.sub(r"[^a-z0-9-]+", "-", d.get("slug", "captured-mistake").lower()).strip("-")[:60] or "captured-mistake"
    path = os.path.join(PENDING, slug + ".md")
    os.makedirs(PENDING, exist_ok=True)
    q = lambda s: '"' + str(s).replace('"', "'").replace("\n", " ") + '"'
    body = (f"---\nid: {slug}\ndate: {datetime.date.today()}\nsource: captured automatically; transcript {tp}\nstatus: pending\n"
            f"asked: false\nlevel: advice\nhis_words: {q(prompt.strip()[:300])}\nsituation:\n"
            + "".join(f"  - {q(x)}\n" for x in d["situation"])
            + f"wrong: {q(d.get('wrong', ''))}\nright: {q(d.get('right', ''))}\nlesson: {q(d.get('lesson', ''))}\n"
            f"replay: {q(d.get('replay', ''))}\npass_if:\n" + "".join(f"  - {q(x)}\n" for x in d.get("pass_if", []))
            + f"occurrences:\n  - {q(line)}\n---\n")
    open(path, "w", encoding="utf-8").write(body)
    _todo(slug)
    return path


def _todo(slug):
    lines = open(TODO, encoding="utf-8").read().split("\n")
    i = lines.index("Done") if "Done" in lines else len(lines)
    lines.insert(i, f"- [ ] review captured case `{slug}` (cases/_pending/{slug}.md): add, edit or discard")
    open(TODO, "w", encoding="utf-8").write("\n".join(lines))


def ask_notes():
    """One note per pending case not yet asked about; marks it asked. Injected by the next UserPromptSubmit."""
    out = []
    for f in sorted(os.listdir(PENDING)) if os.path.isdir(PENDING) else []:
        p = os.path.join(PENDING, f)
        d = index.parse(p) if f.endswith(".md") else {}
        if d.get("asked") == "false":
            t = open(p, encoding="utf-8").read().replace("asked: false", "asked: true", 1)
            open(p, "w", encoding="utf-8", newline="").write(t)
            out.append(f"Captured a possible mistake: {d.get('lesson', '')} (cases/_pending/{f}). Ask the owner: add it to the "
                       "knowledge? and how: as a lesson brought in when the situation repeats (level: advice), as a check "
                       "before finishing (level: check), or as a hard rule (level: rule); or edit or discard. Apply his "
                       "answer: move the file to cases/ with the level set, edit it, or delete it.")
    return out
