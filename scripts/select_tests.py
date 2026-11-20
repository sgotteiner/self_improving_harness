"""Which suites of run_chosen_checks.py a change needs: files changed -> {suite name: (why, extra args)}. Pure mapping, no running."""
import os, subprocess

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CAPTURE = {"index", "embed", "retrieve", "validate", "casesave", "capture"}


def changed_files(since=None):
    """Paths (relative to the setup root, forward slashes) changed since the last commit, or since `since`; plus untracked."""
    def git(*a):
        p = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return [l.strip() for l in p.stdout.splitlines() if l.strip()]
    return sorted(set(git("diff", "--name-only", "--relative", since or "HEAD") + git("ls-files", "--others", "--exclude-standard")))


def uncovered(files):
    """The changed .py files no check covers (select gives them no suite): reported, never answered with a whole suite."""
    return [f for f in files if f.endswith(".py") and not select([f])]


def select(files):
    """{suite: (why, extra args)} in run order; empty when nothing relevant changed."""
    why = {}

    def pick(suite, f):
        why.setdefault(suite, []).append(os.path.basename(f))

    for f in files:
        d, base = os.path.dirname(f), os.path.splitext(os.path.basename(f))[0]
        if d == "scripts/recall" and f.endswith(".py"):
            if base in CAPTURE:
                pick("capture check", f)
        elif f.startswith("cases/"):
            pick("capture check", f)
        elif f.startswith(("skills/sdd/", "skills/system-map/")):
            pick("sdd tests", f)
    order = ["sdd tests", "capture check"]
    return {s: (", ".join(sorted(set(why[s]))[:4]) + " changed", []) for s in order if s in why}
