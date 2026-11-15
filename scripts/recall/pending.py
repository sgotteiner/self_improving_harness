"""What mistake capture (capture.py) and decision capture (decisions.py) share: drafts waiting for his answer in a
pending folder, the to-do line that tracks each, the one-time question, and small text helpers."""
import json, os, re

import ctx, index

TODO = os.path.join(ctx.ROOT, "tasks", "todo.md")


def q(s):
    """A value as a double-quoted one-line frontmatter scalar."""
    return '"' + str(s).replace('"', "'").replace("\n", " ").strip() + '"'


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


def ask_notes(folder, render):
    """[(path, note)] for each draft in `folder` not yet asked about; render(slug, parsed frontmatter) -> the note.
    hook.py prints the notes and only then calls mark_asked(path)."""
    out = []
    for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        p = os.path.join(folder, f)
        d = index.parse(p) if f.endswith(".md") else {}
        if d.get("asked") == "false":
            out.append((p, render(f[:-3], d)))
    return out


def mark_asked(path):
    t = open(path, encoding="utf-8", newline="").read().replace("asked: false", "asked: true", 1)
    open(path, "w", encoding="utf-8", newline="").write(t)
