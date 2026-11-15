"""The diary side of decision capture: which diary a project has, what it already holds, and the append of an approved
draft (decisions.py has the detection). Append-only: an entry goes under the "captured decisions" section and nothing
existing is edited. Also resolves the flags file next to a diary (flags.py)."""
import json, os, re

import ctx, embed, index, mdfile, pending

PENDING = os.path.join(ctx.ROOT, "diary-pending")
SECTION = "## Feature: captured decisions (not yet filed under their feature)"
DIARY_SETUP = os.path.join(os.path.dirname(ctx.ROOT), "Vault", "Projects", "Claude_Setup", "DESIGN_DECISIONS_DIARY.md")
FLAGS_SETUP = os.path.join(os.path.dirname(DIARY_SETUP), "DIARY_FLAGS.md")  # Claude's own choices, kept out of his diary
FLAGS_NAME = "DIARY_FLAGS.md"


def project_of(tp):
    """The last cwd recorded in the transcript (the session may have moved), else ''."""
    cwd = ""
    try:
        for l in open(tp, encoding="utf-8"):
            try:
                cwd = json.loads(l).get("cwd") or cwd
            except ValueError:
                continue
    except OSError:
        pass
    return cwd


def _docs_line(cwd, name):
    """The paths in backticks on the line `- **<name>:** ...` of the CLAUDE.md section "Project documents"."""
    try:
        t = open(os.path.join(cwd, "CLAUDE.md"), encoding="utf-8").read()
    except OSError:
        return []
    sec = re.search(r"^## Project documents.*?(?=^## |\Z)", t, re.S | re.M)
    m = re.search(r"^[-*]\s*\*{0,2}" + name + r":?\*{0,2}:?(.*)$", sec.group(0) if sec else "", re.M | re.I)
    return re.findall(r"`([^`]+\.md)`", m.group(1)) if m else []


def diary_for(cwd):
    """Path of the diary of the project at cwd, or '' (then he is asked where it is). The setup keeps its diary in the
    vault; a project names it on the Diary line of "Project documents" in its CLAUDE.md. No guessing from file names."""
    if not cwd:
        return ""
    if os.path.normcase(os.path.normpath(cwd)) == os.path.normcase(os.path.normpath(ctx.ROOT)):
        return DIARY_SETUP if os.path.exists(DIARY_SETUP) else ""
    for rel in _docs_line(cwd, "Diary")[:1]:
        p = os.path.normpath(os.path.join(cwd, rel))
        if os.path.exists(p):
            return p
    return ""


def flags_for(cwd):
    """The flags file of the project at cwd: the setup's in the vault; a project's is the second path on its Diary line, or
    DIARY_FLAGS.md next to its diary. '' when there is none (a missing file is not created)."""
    diary = diary_for(cwd)
    if not diary:
        return ""
    if diary == DIARY_SETUP:
        return FLAGS_SETUP if os.path.exists(FLAGS_SETUP) else ""
    for rel in _docs_line(cwd, "Diary")[1:]:
        if os.path.exists(os.path.join(cwd, rel)):
            return os.path.normpath(os.path.join(cwd, rel))
    p = os.path.join(os.path.dirname(diary), FLAGS_NAME)
    return p if os.path.exists(p) else ""


def entries(diary):
    """{title: 'title idea'} of the diary's entries (### heading + its **Idea:** line)."""
    try:
        text = open(diary, encoding="utf-8").read()
    except OSError:
        return {}
    out = {}
    for m in re.finditer(r"^### (.+?)\s*$(.*?)(?=^#{1,3} |\Z)", text, re.S | re.M):
        idea = re.search(r"\*\*Idea:\*\*\s*(.*)", m.group(2))
        out[m.group(1)] = m.group(1) + " " + (idea.group(1) if idea else "")
    return out


def _pending_docs():
    out = {}
    for f in sorted(os.listdir(PENDING)) if os.path.isdir(PENDING) else []:
        if f.endswith(".md"):
            d = index.parse(os.path.join(PENDING, f))
            out["pending:" + f] = d.get("title", "") + " " + d.get("idea", "")
    return out


def duplicate(title, idea, diary):
    """(id, score) of an existing diary entry or pending draft the draft matches at >= ctx.SAME, else None."""
    docs = {k: [v] for k, v in {**entries(diary), **_pending_docs()}.items() if v.strip()}
    if not docs:
        return None
    sc = embed.scores(title + " " + idea, docs)
    best = max(sc, key=sc.get)
    return (best, sc[best]) if sc[best] >= ctx.SAME else None


def format_entry(d):
    return (f"### {d['title']}\ntags: kind={d.get('kind', 'decision')} · attribution=your-design · "
            f"portable={d.get('portable', 'no')} · signature=no · importance={d.get('importance', 'normal')}\n"
            f"anchor: {d.get('date', '')} · none · session {d.get('session', '')}\n"
            f"**Idea:** {d.get('idea', '')}\n**Why:** {d.get('why', '')}\n")


def _draft(slug):
    """(draft path, None) or (None, exit code) after printing why the slug cannot be used."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", slug or ""):
        print(f"bad slug {slug!r}: a draft name has no path separators")
        return None, 2
    p = os.path.join(PENDING, slug + ".md")
    if not os.path.exists(p):
        print(f"no pending draft {slug}")  # approved or discarded already: nothing to do, not an error
        return None, 0
    return p, 0


def approve(slug, target=None):
    """Append the draft to the project's diary and delete the draft. Returns the exit code."""
    p, code = _draft(slug)
    if not p:
        return code
    d = index.parse(p)
    target = target or d.get("target")
    if not target or not os.path.exists(target):
        print(f"no diary found for this draft (project {d.get('project')!r}); pass the diary path as a second argument")
        return 1
    text = mdfile.read(target)  # read right before the write, so an edit made since the draft is not lost
    if re.search(r"^### " + re.escape(d["title"]) + r"\s*$", text, re.M):
        print(f"'{d['title']}' is already in {target}; draft removed")  # an earlier approve died after the write
    else:
        mdfile.write_atomic(target, mdfile.insert_under(text, SECTION, format_entry(d), rule=True))
        print(f"appended '{d['title']}' to {target}")
    os.remove(p)
    pending.todo_remove(f"diary-pending/{slug}.md")
    return 0


def discard(slug):
    p, code = _draft(slug)
    if p:
        os.remove(p)
        pending.todo_remove(f"diary-pending/{slug}.md")
        print("discarded", slug)
    return code
