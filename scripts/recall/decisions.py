"""Decision capture (switch `decision-capture` in slots.json). Mirrors mistake capture (capture.py): on his message a
cheap model detects a design decision (a rule for how something should work, a choice between options, a yes to a design
the assistant just proposed); if so a second call drafts a diary entry into diary-pending/ (local only: that folder is
not in the .gitignore allowlist, so the public setup repo never sees his words); the next message presents it once
("Diary: <title> - '<his words>'. Add it?"); his yes -> `decisions.py approve <slug>` appends it to the project's diary
in the design-diary format, his no -> `discard <slug>`. The rule it serves (CLAUDE.md): the diary is append-only,
suggested in one line, appended only after his yes. Why a hook: the entry used to depend on the main session
remembering to suggest it, and the setup's diary went 3 weeks without one."""
import datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, ctx, embed, index

PENDING = os.path.join(ctx.ROOT, "diary-pending")
TODO = os.path.join(ctx.ROOT, "tasks", "todo.md")
SECTION = "## Feature: captured decisions (not yet filed under their feature)"

DETECT = ("The assistant's previous turn:\n{prev}\n\nThe owner's new message: {prompt}\n\n"
          "Does his message state a DESIGN decision or approve one: a rule for how something should work or be built, a "
          "choice between options, or a 'yes' / 'ok' / 'do it' to a design the assistant just proposed? NOT a decision: "
          "a bug report or 'it doesn't work', a question, a correction of the assistant's behavior or mistake ('I told "
          "you', 'that's wrong', 'you missed'), a request to do a task, a yes to a plain action (run it, commit it), "
          "approval of a finished result, thanks. Reply 'NO' or 'YES | <one sentence: the decision>'.")
DRAFT = ("Draft a design-diary entry for this decision of the owner. Decision: {why}\nThe assistant's previous turn "
         "(context only):\n{prev}\nThe owner's words: {prompt}\n\nReply with JSON only: {{\"title\": \"short title of the "
         "decision\", \"idea\": \"what he decided, 1-2 sentences, in design terms (include the design the assistant "
         "proposed if he said yes to it)\", \"why\": \"the reasoning, quoting HIS words that state it; if he gave no "
         "reason write '(not stated)'; never invent a reason\", \"kind\": \"decision|principle|feature-motivation\", "
         "\"portable\": \"yes|no (would it apply in other projects)\", \"importance\": \"normal|high\"}}.")


def _json(s):
    m = re.search(r"\{.*\}", s, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


def _q(s):
    return '"' + str(s).replace('"', "'").replace("\n", " ").strip() + '"'


def project_of(tp):
    """cwd recorded in the transcript (first entry that has one), else ''."""
    try:
        for l in open(tp, encoding="utf-8"):
            try:
                c = json.loads(l).get("cwd")
            except ValueError:
                continue
            if c:
                return c
    except OSError:
        pass
    return ""


def diary_for(cwd):
    """Path of the diary of the project at cwd, or ''. The setup itself keeps its diary in the vault; a project lists
    its diary in its CLAUDE.md or keeps it in docs/."""
    if not cwd:
        return ""
    c = os.path.normcase(os.path.normpath(cwd))
    if c == os.path.normcase(os.path.normpath(ctx.ROOT)):
        p = os.path.join(os.path.dirname(ctx.ROOT), "Vault", "Projects", "Claude_Setup", "DESIGN_DECISIONS_DIARY.md")
        return p if os.path.exists(p) else ""
    try:
        for m in re.finditer(r"`([^`]*diary[^`]*\.md)`", open(os.path.join(cwd, "CLAUDE.md"), encoding="utf-8").read(), re.I):
            p = os.path.normpath(os.path.join(cwd, m.group(1)))
            if os.path.exists(p):
                return p
    except OSError:
        pass
    for d in (os.path.join(cwd, "docs"), cwd):
        try:
            for f in sorted(os.listdir(d)):
                if "diary" in f.lower() and f.lower().endswith(".md") and "flags" not in f.lower():
                    return os.path.join(d, f)
        except OSError:
            pass
    return ""


def entries(diary):
    """{title: 'title idea'} of the diary's entries (### heading + its **Idea:** line)."""
    out = {}
    try:
        text = open(diary, encoding="utf-8").read()
    except OSError:
        return out
    for m in re.finditer(r"^### (.+?)\s*$(.*?)(?=^#{1,3} |\Z)", text, re.S | re.M):
        idea = re.search(r"\*\*Idea:\*\*\s*(.*)", m.group(2))
        out[m.group(1)] = m.group(1) + " " + (idea.group(1) if idea else "")
    return out


def _pending_docs():
    out = {}
    for f in sorted(os.listdir(PENDING)) if os.path.isdir(PENDING) else []:
        if f.endswith(".md"):
            d = index.parse(os.path.join(PENDING, f))
            out["pending:" + f] = (d.get("title", "") + " " + d.get("idea", ""))
    return out


def duplicate(title, idea, diary):
    """(id, score) of an existing diary entry or pending draft the draft matches at >= capture.SAME, else None."""
    import capture
    docs = {k: [v] for k, v in {**entries(diary), **_pending_docs()}.items() if v.strip()}
    if not docs:
        return None
    sc = embed.scores(title + " " + idea, docs)
    best = max(sc, key=sc.get)
    return (best, sc[best]) if sc[best] >= capture.SAME else None


def process(prompt, tp):
    """On a new human prompt. Returns (path of a new draft or None, brain tokens)."""
    prev, tools = ctx.last_turn(tp, prompt.strip())
    if "Add it?" in prev and "Diary:" in prev:  # his message answers a diary question; it is not a decision
        return None, 0
    out, tok = brain.ask(DETECT.format(prev=prev[:2500] or "(none)", prompt=prompt), tag="decision-detect")
    if not out.upper().startswith("YES"):
        return None, tok
    why = out.partition("|")[2].strip()
    raw, t2 = brain.ask(DRAFT.format(why=why, prev=prev[:2500] or "(none)", prompt=prompt), tag="decision-draft")
    tok += t2
    d = _json(raw)
    if not d or not d.get("title") or not d.get("idea"):
        return None, tok
    cwd = project_of(tp)
    diary = diary_for(cwd)
    dup = duplicate(d["title"], d["idea"], diary)
    if dup:
        ctx.log(f"decisions: skipped, matches {dup[0]} at {dup[1]:.2f}")
        return None, tok
    slug = re.sub(r"[^a-z0-9-]+", "-", d["title"].lower()).strip("-")[:60] or "decision"
    path = os.path.join(PENDING, slug + ".md")
    os.makedirs(PENDING, exist_ok=True)
    kind = d.get("kind") if d.get("kind") in ("decision", "principle", "feature-motivation") else "decision"
    body = (f"---\nid: {slug}\ndate: {datetime.date.today()}\nproject: {_q(cwd)}\ntarget: {_q(diary)}\n"
            f"session: {os.path.splitext(os.path.basename(tp))[0][:8]}\nstatus: pending\nasked: false\n"
            f"title: {_q(d['title'])}\nkind: {kind}\nportable: {'yes' if str(d.get('portable')).lower().startswith('y') else 'no'}\n"
            f"importance: {'high' if str(d.get('importance')).lower() == 'high' else 'normal'}\n"
            f"idea: {_q(d['idea'])}\nwhy: {_q(d.get('why') or '(not stated)')}\nhis_words: {_q(prompt.strip())}\n---\n")
    open(path, "w", encoding="utf-8").write(body)
    try:
        _todo(slug)
    except OSError as e:
        ctx.log(f"decisions: todo not updated: {e!r}")
    return path, tok


def _todo(slug):
    lines = open(TODO, encoding="utf-8").read().split("\n") if os.path.exists(TODO) else []
    i = lines.index("Done") if "Done" in lines else len(lines)
    lines.insert(i, f"- [ ] diary entry suggested `{slug}` (diary-pending/{slug}.md): add or discard")
    open(TODO, "w", encoding="utf-8").write("\n".join(lines))


def _untodo(slug):
    if os.path.exists(TODO):
        lines = [l for l in open(TODO, encoding="utf-8").read().split("\n") if f"diary-pending/{slug}.md" not in l]
        open(TODO, "w", encoding="utf-8").write("\n".join(lines))


def ask_notes():
    """[(path, note)] for each draft not yet asked about; hook.py prints them and then calls capture.mark_asked(path)."""
    out = []
    for f in sorted(os.listdir(PENDING)) if os.path.isdir(PENDING) else []:
        p = os.path.join(PENDING, f)
        d = index.parse(p) if f.endswith(".md") else {}
        if d.get("asked") == "false":
            slug = f[:-3]
            out.append((p, f"Diary: {d.get('title', '')} - '{d.get('his_words', '')[:200]}'. Add it? Ask the owner exactly this "
                           f"one line (the rule: append to the diary only after his yes). If he says yes run `python -I "
                           f"scripts/recall/decisions.py approve {slug}`; if no, `python -I scripts/recall/decisions.py "
                           f"discard {slug}`; no answer: leave it."))
    return out


def format_entry(d):
    return (f"### {d['title']}\ntags: kind={d.get('kind', 'decision')} · attribution=your-design · "
            f"portable={d.get('portable', 'no')} · signature=no · importance={d.get('importance', 'normal')}\n"
            f"anchor: {d.get('date', '')} · none · session {d.get('session', '')}\n"
            f"**Idea:** {d.get('idea', '')}\n**Why:** {d.get('why', '')}\n")


def approve(slug, target=None):
    """Append the draft to the project's diary (append-only: nothing existing is edited) and delete the draft."""
    p = os.path.join(PENDING, slug + ".md")
    d = index.parse(p)
    target = target or d.get("target")
    if not target or not os.path.exists(target):
        raise SystemExit(f"no diary found for this draft (project {d.get('project')!r}); pass the diary path as a second argument")
    text = open(target, encoding="utf-8").read()
    add = ("" if text.endswith("\n") else "\n") + ("" if SECTION in text else "\n---\n\n" + SECTION + "\n") + "\n" + format_entry(d)
    open(target, "a", encoding="utf-8", newline="").write(add.replace("\n", "\r\n") if "\r\n" in text else add)
    os.remove(p)
    _untodo(slug)
    print(f"appended '{d['title']}' to {target}")


def discard(slug):
    os.remove(os.path.join(PENDING, slug + ".md"))
    _untodo(slug)
    print("discarded", slug)


if __name__ == "__main__" and len(sys.argv) >= 3 and sys.argv[1] in ("approve", "discard"):
    approve(*sys.argv[2:4]) if sys.argv[1] == "approve" else discard(sys.argv[2])
