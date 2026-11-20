"""What mistake capture (capture.py) and decision capture (decisions.py) share: drafts waiting for his answer in a
pending folder, the to-do line that tracks each, the one-time question, and small text helpers."""
import json, os, re

import ctx, index

TODO = os.path.join(ctx.ROOT, "tasks", "todo.md")
DEFAULT_SLUG = "captured-mistake"  # the id of a lesson whose session gave no usable slug


def q(s):
    """A value as a double-quoted one-line frontmatter scalar."""
    return '"' + str(s).replace('"', "'").replace("\n", " ").strip() + '"'


def case_text(slug, d, raw, date):
    """The file text of a lesson captured by the session (capwrite.write fields: lesson, situation, did); the owner's raw words stay local."""
    return (f"---\nid: {slug}\ndate: {date}\nlevel: advice\nhis_words: {q(raw)}\nsituation:\n  - {q(d['situation'])}\n"
            f"wrong: {q(d['did'])}\nright: {q('(not stated)')}\nlesson: {q(d['lesson'])}\nreplay: {q('(not stated)')}\n"
            f"pass_if:\n  - {q('(not stated)')}\noccurrences: 0\n---\n")


def json_of(s):
    """The first {...} of a model reply as a dict, or None."""
    m = re.search(r"\{.*\}", s, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


def slugify(s, default, n=60):
    return re.sub(r"[^a-z0-9-]+", "-", str(s).lower()).strip("-")[:n] or default


def todo_add(line):
    """Insert a to-do line above the 'Done' heading (or at the end)."""
    lines = open(TODO, encoding="utf-8").read().split("\n") if os.path.exists(TODO) else []
    lines.insert(lines.index("Done") if "Done" in lines else len(lines), line)
    open(TODO, "w", encoding="utf-8").write("\n".join(lines))


def todo_remove(marker):
    """Drop the to-do lines that contain `marker`."""
    if os.path.exists(TODO):
        lines = [l for l in open(TODO, encoding="utf-8").read().split("\n") if marker not in l]
        open(TODO, "w", encoding="utf-8").write("\n".join(lines))


def ask_notes(folder, render, unasked_only=True):
    """[(path, note)] for each draft in `folder` (not yet asked about, or all of them); render(slug, parsed frontmatter) -> the
    question. drafts.py shows them when he asks to review the drafts."""
    out = []
    for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        p = os.path.join(folder, f)
        d = index.parse(p) if f.endswith(".md") else {}
        if d.get("asked") == "false" or not unasked_only and d:
            out.append((p, render(f[:-3], d)))
    return out


def mark_asked(path):
    t = open(path, encoding="utf-8", newline="").read().replace("asked: false", "asked: true", 1)
    open(path, "w", encoding="utf-8", newline="").write(t)
