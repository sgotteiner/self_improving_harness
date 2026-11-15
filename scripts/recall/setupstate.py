"""The setup's files as git sees them: which setup files a turn changed (a snapshot taken at his message against `git status`
now), and whether a turn edited one. Ignored and generated files, drafts and the to-do list do not count."""
import json, os, subprocess, tempfile

import ctx, transcript

EDIT_TOOLS = ("Edit", "MultiEdit", "Write", "NotebookEdit")
SETUP_PATHS = ("CLAUDE.md", "settings.json", "slots.json", "agents/", "skills/", "scripts/", "cases/", "mods/",
               "tasks/delegation-draft.md")
SETUP_SKIP = ("cases/_pending/", "cases/history/", "tasks/todo.md", "scripts/recall/results/")  # drafts, to-do, generated
GIT_TIMEOUT = 20  # seconds for `git status`; on failure the git view is skipped, the edit tools still count
STATE = os.path.join(tempfile.gettempdir(), "recall-turn")  # per session: the setup's files as they were at his message


def setup_rel(path, root=ctx.ROOT):
    """Path relative to the setup root if it is a setup file that counts, else None."""
    if not path:
        return None
    p = path.replace("/c/", "C:/", 1) if path.startswith("/c/") else path
    p = os.path.normpath(p if os.path.isabs(p) else os.path.join(root, p))
    root = os.path.normpath(root)
    if not os.path.normcase(p).startswith(os.path.normcase(root) + os.sep):
        return None
    rel = p[len(root) + 1:].replace(os.sep, "/")
    return rel if rel.startswith(SETUP_PATHS) and not rel.startswith(SETUP_SKIP) else None


def git_state(root):
    """{setup file: (mtime, size)} of what `git status --porcelain` lists (ignored files are not listed), or None."""
    try:
        out = subprocess.run(["git", "-C", root, "status", "--porcelain", "-uall"], capture_output=True, text=True,
                             encoding="utf-8", timeout=GIT_TIMEOUT).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    st = {}
    for l in out.splitlines():
        rel = setup_rel(l[3:].split(" -> ")[-1].strip('"'), root)
        if rel:
            try:
                s = os.stat(os.path.join(root, rel))
                st[rel] = [s.st_mtime_ns, s.st_size]
            except OSError:
                st[rel] = [0, -1]
    return st


def _snap(tp):
    return os.path.join(STATE, os.path.splitext(os.path.basename(tp))[0] + ".json")


def save_snapshot(tp, root=ctx.ROOT):
    """At his message (hook.py): the setup's state, to tell later what this turn changed. A snapshot that cannot be taken
    is deleted, so the previous turn's one is never used for this turn."""
    try:
        state = git_state(root)
        if state is None:
            raise OSError("git status failed")
        os.makedirs(STATE, exist_ok=True)
        json.dump(state, open(_snap(tp), "w", encoding="utf-8"))
    except Exception:
        if os.path.exists(_snap(tp)):
            os.remove(_snap(tp))
        raise


def git_changed(tp, root):
    """Setup files that differ from the snapshot taken at his message; [] when there is no snapshot or no git."""
    try:
        before = json.load(open(_snap(tp), encoding="utf-8"))
    except (OSError, ValueError):
        return []
    now = git_state(root)
    return [r for r, v in (now or {}).items() if before is not None and before.get(r) != v]


def setup_edited(tp, exclude=None, root=ctx.ROOT):
    """True when the latest turn before the message `exclude` edited a setup file with an edit tool."""
    es = ctx.entries(tp)
    start = ctx._start(es, exclude) * transcript.SEQ
    return any(c["name"] in EDIT_TOOLS and setup_rel(c["input"].get("file_path", ""), root)
               for c in transcript.calls(es) if c["seq"] >= start)
