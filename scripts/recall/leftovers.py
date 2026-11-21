"""Everything that is still open in a project, at once, for the message step's DONE-ASK flag (doneask.py): the unchecked items of its
todo, the open IDEAS rows added or changed today, the proposals waiting for his answer, the background agents still running in the
session, `git status --short` of the project's repo (not this repo's live cases/ records: they are committed at done) and of the
Vault, and what is marked unverified in today's IDEAS rows and in the SDD criteria changed today (from git). Read-only; fails open.
Usage: python -I scripts/recall/leftovers.py [project folder] [transcript]"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

REPORT_MAX = 3000  # chars of the whole list (the hook's output is capped)
ITEM_MAX = 160  # chars kept of one item
GIT_LINES_MAX = 25  # `git status --short` lines kept per repo
GIT_TIMEOUT = 20  # seconds per git call
VAULT = os.path.join(os.path.dirname(ctx.ROOT), "Vault")
UNVERIFIED = re.compile(r"unverified|not verified|not run live", re.I)
VERIFIED = re.compile(r"(?<!not )verified|checked live", re.I)  # an SDD line that says so is not an open item
FINISHED = ("done", "closed")  # IDEAS statuses whose rows are not open items
UNCHECKED = re.compile(r"^\s*- \[ \]\s*(.*)")
NOTHING = "(nothing left open)"


def _git(repo, *args):
    try:
        p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT)
        return p.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def added_today(path):
    """The lines added to the file by today's commits (oldest first) and by its uncommitted change, from git, that are still in the file."""
    repo, name = os.path.dirname(path), os.path.basename(path)
    out = _git(repo, "log", "--since=midnight", "--reverse", "--format=", "-p", "-U0", "--", name) + _git(repo, "diff", "HEAD", "-U0", "--", name)
    try:
        now = set(open(path, encoding="utf-8").read().splitlines())
    except OSError:
        return []
    return [l[1:] for l in out.splitlines() if l.startswith("+") and not l.startswith("+++") and l[1:] in now]


def _cut(t):
    return " ".join(t.split())[:ITEM_MAX]


def todo_items(path):
    try:
        return [_cut(m.group(1)) for l in open(path, encoding="utf-8") if (m := UNCHECKED.match(l))]
    except OSError:
        return []


def today_rows(path):
    """The IDEAS rows touched today, as their latest version: {thread: row}."""
    rows = {}
    for l in added_today(path):
        cells = l.split("|")
        if l.startswith("|") and len(cells) > 3 and not set(cells[1].strip()) <= set("-: "):
            rows[cells[1].strip()] = l
    return rows


def open_rows(rows):
    return [_cut(l.split("|")[1]) + " (" + _cut(l.split("|")[2]) + ")" for l in rows.values() if l.split("|")[2].strip().lower().startswith("open")]


def unverified(rows, sdd):
    """Unfinished rows whose result or next cell is marked unverified, and SDD criteria lines changed today that are and do not also say verified."""
    hits = [c[1] for c in (l.split("|") for l in rows.values()) if not c[2].strip().lower().startswith(FINISHED) and UNVERIFIED.search("|".join(c[4:]))]
    return [_cut(t) for t in hits + [l for l in added_today(sdd) if l.startswith("- criteria:") and UNVERIFIED.search(l) and not VERIFIED.search(l)]]


def dirty(repos):
    out, seen = [], set()
    for r in repos:
        if os.path.normcase(os.path.realpath(r)) in seen or not os.path.isdir(r):
            continue
        seen.add(os.path.normcase(os.path.realpath(r)))
        lines = [_cut(l) for l in _git(r, "status", "--short").splitlines() if not (os.path.normcase(r) == os.path.normcase(ctx.ROOT) and l[3:].startswith("cases/"))]
        out += [f"{os.path.basename(r)}: {l}" for l in lines[:GIT_LINES_MAX]] + ([f"{os.path.basename(r)}: ... {len(lines) - GIT_LINES_MAX} more"] * (len(lines) > GIT_LINES_MAX))
    return out


def proposals_waiting():
    import proposals
    return [f"{r['pid']} ({r['status']}): {_cut(r['text'])}" for r in proposals.read() if r["status"] in (proposals.QUEUED,) + proposals.OPEN]


def agents_running(tp):
    import transcript
    return [f"{k}: {_cut(d)}" for k, d in transcript.running(ctx.entries(tp, notices=True))] if tp else []


def report(cwd, tp=""):
    """The leftover list for the project of `cwd` (and the session `tp`, for its running agents) as text; NOTHING when empty."""
    import projcheck
    proj = projcheck.project_dir(cwd or ctx.ROOT) or ctx.ROOT
    docs = projcheck.documents(proj) or projcheck.documents(ctx.ROOT)  # a cwd with no project documents (the Vault, a scratch folder) falls back to the setup's, so its todo never drops out
    first = lambda n: (docs.get(n) or [""])[0]
    parts = {}
    try:
        rows = today_rows(first("Ideas")) if first("Ideas") else {}
        parts = {"Background agents still running": agents_running(tp), "Uncommitted changes": dirty([proj, VAULT]),
                 "Proposals waiting for his answer": proposals_waiting(), "Open IDEAS rows added or changed today": open_rows(rows),
                 "Marked unverified": unverified(rows, first("SDD")) if first("SDD") else [], "Unchecked todo items": todo_items(first("Todo"))}  # the longest part last: the cap cuts it
    except Exception as e:
        ctx.log(f"leftovers: failed: {e!r}")
        return "(the list could not be built; check the todo, the ideas and git status yourself)"
    text = "\n".join(f"{k}:\n" + "\n".join(f"- {i}" for i in v) for k, v in parts.items() if v)
    return (text if len(text) <= REPORT_MAX else text[:REPORT_MAX] + "\n(cut)") or NOTHING


if __name__ == "__main__":
    print(report(sys.argv[1] if len(sys.argv) > 1 else os.getcwd(), sys.argv[2] if len(sys.argv) > 2 else ""))
