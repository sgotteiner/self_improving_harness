"""SessionStart hook (slot session-map): the session starts knowing its project. Prints the project's map top level (root and its
boxes, one line each, children counted), the State lines of its SDD note and the open items of its Todo, with where the full
map and SDD are. The map's data T is JSON (map-data.js writes it with JSON.stringify), read without node. No project or no map
= prints nothing; any error is logged and prints nothing (a session start is never blocked). Stdlib only."""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

SLOT = "session-map"
CAP = 2000  # chars of the whole output (about 500 tokens); Todo items are dropped first, then descriptions shortened, then names only
DESC_MAX, DESC_MIN, DESC_STEP = 110, 40, 10  # chars of a box description: from DESC_MAX down to DESC_MIN; below it, names only
ROOT_EXTRA = 60  # the root's description gets this many chars more than a box's
TODO_MAX, TODO_CUT = 3, 110  # open Todo items shown, chars of each
STATE_CUT = 300  # chars of one State line
MARK = "/* ───────── index"  # where the data T ends in a map page (map-data.js MARK)
STATE = re.compile(r"^(open|state|status):\s*(.+)$", re.I)  # State lines of an SDD note: above its first `## ` section
ITEM = re.compile(r"^\s*[-*]\s*\[ \]\s*(.+)$")


def cut(s, n):
    """s in at most n chars, cut at a word boundary."""
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:max(n - 3, 0)].rsplit(" ", 1)[0].rstrip(",;:") + "..."


def first_sentence(s):
    return re.split(r"(?<=[.!?])\s", " ".join(str(s).split()), 1)[0]


def read_T(path):
    html = open(path, encoding="utf-8").read()
    a = html.index("const T=", html.index("<script")) + len("const T=")
    b = html.rindex(MARK)
    return json.loads(html[a:b].strip().rstrip(";"))


def find_map(sdd):
    """The map next to the SDD: the .html in its folder whose data T lists the SDD file, else ''."""
    d = os.path.dirname(sdd)
    for f in sorted(os.listdir(d)):
        if f.endswith(".html"):
            try:
                T = read_T(os.path.join(d, f))
            except (OSError, ValueError):
                continue
            if any(os.path.basename(s) == os.path.basename(sdd) for s in T.get("sdd", [])):
                return os.path.join(d, f), T
    return "", None


def state_lines(sdd):
    out = []
    for l in open(sdd, encoding="utf-8").read().splitlines():
        if l.startswith("## "):
            break
        m = STATE.match(l.strip())
        if m:
            out.append(f"{m.group(1).lower()}: {cut(m.group(2), STATE_CUT)}")
    return out


def todo_items(path):
    try:
        items = [m.group(1) for m in map(ITEM.match, open(path, encoding="utf-8").read().splitlines()) if m]
    except OSError:
        return []
    return [re.sub(r"[*`]", "", i) for i in items]


def _render(name, map_path, sdd, T, state, todo, d):
    """The output with box descriptions cut to d chars (d = 0: names only) and the given Todo items."""
    desc = lambda c, n: f": {cut(first_sentence(c.get('desc', '')), n)}" if d else ""
    lines = [f"Project {name}. Full map: {map_path} ; SDD: {sdd} (read deeper only when needed).",
             f"{T['name']}{desc(T, d + ROOT_EXTRA)}"] + state
    lines += [f"- {c['name']}{desc(c, d)} ({len(c.get('children', []))})" for c in T.get("children", [])]
    if todo:
        lines += ["Open todo:"] + [f"- {cut(i, TODO_CUT)}" for i in todo]
    return "\n".join(lines)


def build(name, map_path, sdd, T, state, todo):
    """The longest descriptions that fit CAP, dropping Todo items before shortening; then names only; then a hard cut."""
    todo = todo[:TODO_MAX]
    for d in list(range(DESC_MAX, DESC_MIN - 1, -DESC_STEP)) + [0]:
        for n in range(len(todo), -1, -1):
            out = _render(name, map_path, sdd, T, state, todo[:n], d)
            if len(out) <= CAP:
                return out
    return out[:CAP]


def run(cwd):
    import projcheck
    d = projcheck.project_dir(cwd) if cwd else ""
    docs = projcheck.documents(d) if d else None
    sdd = next((p for p in (docs or {}).get("SDD", []) if os.path.exists(p)), "")
    if not sdd:
        return ""
    map_path, T = find_map(sdd)
    if not T:
        return ""
    name = os.path.basename(d)
    todo = next((todo_items(p) for p in docs.get("Todo", []) if os.path.exists(p)), [])
    return build(name, map_path, sdd, T, state_lines(sdd), todo)


def main():
    try:
        if not ctx.enabled(SLOT) or ctx.skip_env("RECALL_SESSIONMAP"):
            return
        j = json.loads(sys.stdin.read() or "{}")
        cwd = j.get("cwd") or ""
        if not cwd:
            import diary
            cwd = diary.project_of(j.get("transcript_path") or "")
        out = run(cwd)
        sys.stdout.reconfigure(encoding="utf-8")  # the console's code page would garble or reject the text
        out and print(out)
    except Exception as e:
        ctx.log(f"sessionmap: failed: {e!r}")


if __name__ == "__main__":
    main()
