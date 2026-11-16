"""Project check (switch `project-check` in slots.json): on the first message of the day in a project, the project's documents are
compared with the setup's rules and what is missing or stale is told to the owner once, in a few lines. Read-only: nothing
is fixed here. The rules (CLAUDE.md, "Project documents"): five documents exist (SDD, Diary, Ideas, Tests, Todo); the SDD is
in the sdd skill's format (its validator passes); a map is drawn from it and its sddCommit is the SDD's last commit; no
'(inferred)' in the diary; the SDD's git hooks are installed (they redraw the map and refuse an invalid SDD)."""
import datetime, hashlib, json, os, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, diary, mdfile

NAMES = ("SDD", "Diary", "Ideas", "Tests", "Todo")
SCRIPTS = os.path.join(ctx.ROOT, "skills", "sdd", "scripts")
STATE = os.path.join(tempfile.gettempdir(), "recall-projcheck")  # per project and day: the check ran already
VAULT_DOCS = os.path.dirname(diary.DIARY_SETUP)  # the setup's own documents live in its vault folder
SETUP_DOCS = {"SDD": [os.path.join(VAULT_DOCS, "Project.md")], "Diary": [diary.DIARY_SETUP], "Ideas": [os.path.join(VAULT_DOCS, "IDEAS.md")],
              "Tests": [os.path.join(VAULT_DOCS, "Tests.md")], "Todo": [os.path.join(ctx.ROOT, "tasks", "todo.md")]}


def project_dir(cwd):
    """The folder of the project: cwd, or the nearest parent (up to 4) that has a CLAUDE.md or a .git; '' when none."""
    d = os.path.normpath(cwd or "")
    for _ in range(5):
        if d and (os.path.exists(os.path.join(d, "CLAUDE.md")) or os.path.exists(os.path.join(d, ".git"))):
            return d
        d = os.path.dirname(d)
    return ""


def documents(cwd):
    """{name: [paths]} or None when the CLAUDE.md names no "Project documents". The setup's are fixed (its vault folder)."""
    if os.path.normcase(cwd) == os.path.normcase(os.path.normpath(ctx.ROOT)):
        return SETUP_DOCS
    try:
        text = open(os.path.join(cwd, "CLAUDE.md"), encoding="utf-8").read()
    except OSError:
        return None
    if "## Project documents" not in text:
        return None
    return {n: [os.path.normpath(os.path.join(cwd, r)) for r in diary._docs_line(cwd, n)] for n in NAMES}


def node(script, *args):
    """(exit code, output) of one of the sdd skill's scripts; (None, '') when node is missing or the call fails."""
    exe = shutil.which("node")
    if not exe:
        return None, ""
    try:
        p = subprocess.run([exe, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True, encoding="utf-8", timeout=30)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return None, ""


def hooks_installed(sdd):
    try:
        out = subprocess.run(["git", "-C", os.path.dirname(sdd), "rev-parse", "--git-path", "hooks"], capture_output=True, text=True, timeout=20).stdout.strip()
        return "sdd-hook.js" in open(os.path.join(os.path.dirname(sdd), out, "post-commit"), encoding="utf-8").read()
    except (OSError, subprocess.SubprocessError):
        return False


def sdd_problems(path):
    code, out = node("validate-sdd.js", path)
    if code == 1:
        n = out.splitlines()[-1] if out else "problems"
        return [f"the SDD {os.path.basename(path)} is not in the sdd skill's format ({n}; first: {out.splitlines()[0][:110]})"]
    out = []
    code, js = node("sdd-maps.js", path)
    try:
        maps = json.loads(js) if code == 0 else None
    except ValueError:
        maps = None
    if maps is not None:
        if not maps:
            out.append(f"no map is drawn from {os.path.basename(path)} (node skills/sdd/scripts/sdd-to-map.js)")
        out += [f"the map {os.path.basename(m['map'])} is out of date: the SDD changed after it was drawn" for m in maps if not m["current"]]
        if not hooks_installed(path):
            out.append("the SDD's git hooks are not installed (they redraw the map and refuse an invalid SDD): node skills/sdd/scripts/install-hooks.js <repo>")
    return out


def check(cwd):
    """[problem, ...] for the project at cwd ([] = clean, or not a project)."""
    cwd = project_dir(cwd)
    if not cwd:
        return []
    docs = documents(cwd)
    if docs is None:
        return ["CLAUDE.md has no 'Project documents' section listing the SDD, diary, ideas, tests and todo"]
    out = []
    for n in NAMES:
        found = [p for p in docs[n] if os.path.exists(p)]
        if not docs[n]:
            out.append(f"{n}: not listed or marked missing")
        elif len(found) < len(docs[n]):
            out.append(f"{n}: listed but not found: {', '.join(os.path.basename(p) for p in docs[n] if p not in found)}")
    for p in (p for p in docs["SDD"] if os.path.exists(p)):
        out += sdd_problems(p)
    for p in (p for p in docs["Diary"] if os.path.exists(p)):
        if mdfile.inferred_why(mdfile.read(p)):
            out.append(f"the diary {os.path.basename(p)} holds '(inferred)': an inferred why belongs in the flags file")
    return out


def first_message(tp, cwd):
    """The note for the main session: at most once per project per day (the first message), None afterwards and when all is in
    order. The marker is written only after the check ran, so a check that failed is tried again on the next message; markers of
    earlier days are removed."""
    proj = project_dir(cwd or diary.project_of(tp))
    if not proj:
        return []
    day = datetime.date.today().isoformat()
    mark = os.path.join(STATE, f"{hashlib.sha1(os.path.normcase(proj).encode()).hexdigest()[:12]}-{day}.done")
    if os.path.exists(mark):
        return []
    problems = check(proj)
    os.makedirs(STATE, exist_ok=True)
    for f in os.listdir(STATE):
        if not f.endswith(f"-{day}.done"):
            try:
                os.remove(os.path.join(STATE, f))
            except OSError:
                pass
    open(mark, "w").close()
    if not problems:
        return []
    return ["Project check (" + os.path.basename(proj) + "): tell the owner once, in a few short lines, what is missing or stale; "
            "do not fix it unless he asks. " + " | ".join(problems)]


if __name__ == "__main__":
    print("\n".join(check(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())) or "project check: all in order")
