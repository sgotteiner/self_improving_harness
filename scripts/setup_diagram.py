"""Draw the live Claude Code setup in the vault: an SVG diagram plus a table.

Reads the config folder (agents, skills, settings, MCP) and rewrites the note and its image.
Prints nothing, so a SessionStart hook can run it at zero context cost.
"""
import datetime
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import setup_svg  # noqa: E402

BASE = os.environ.get("CLAUDE_CONFIG_DIR", r"C:\my_projects\.claude-config")
PROJECTS = r"C:\my_projects"
OUT = r"C:\my_projects\Vault\Projects\Claude_Setup\Setup_Diagram.md"
SVG = OUT[:-3] + ".svg"
RED, GREY = "#dc2626", "#334155"


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def frontmatter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    fields, key = {}, None
    for line in (m.group(1) if m else "").splitlines():
        line = line.split("#", 1)[0].rstrip()
        item = re.match(r"\s+-\s*(.+)", line)
        if item and key:
            if not isinstance(fields.get(key), list):
                fields[key] = []
            fields[key].append(item.group(1).strip())
            continue
        kv = re.match(r"(\w+):\s*(.*)", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val.startswith("["):
                val = [v.strip() for v in val.strip("[]").split(",") if v.strip()]
            fields[key] = val
    return fields


def agents():
    found = []
    for folder, status in (("agents", "live"), ("agents-draft", "draft")):
        for path in sorted(glob.glob(os.path.join(BASE, folder, "*.md"))):
            fm = frontmatter(path)
            as_list = lambda v: v if isinstance(v, list) else ([v] if v else [])
            # Skills the body tells the agent to read when needed (skills/<name>/SKILL.md).
            on_demand = re.findall(r"skills/([\w-]+)/SKILL\.md", open(path, encoding="utf-8").read())
            found.append((fm.get("name", os.path.basename(path)[:-3]), fm.get("model", "inherit"),
                          as_list(fm.get("skills")) + [f"{s} (on demand)" for s in dict.fromkeys(on_demand)],
                          status,
                          [m.rstrip(":") for m in as_list(fm.get("mcpServers"))]))
    return found


def skills():
    names = sorted(os.path.basename(os.path.dirname(p))
                   for p in glob.glob(os.path.join(BASE, "skills", "*", "SKILL.md")))
    ccc = [n for n in names if n.startswith("ccc-")]
    return [n for n in names if not n.startswith("ccc-")], len(ccc)


def mcp_servers():
    servers = {"all projects": list(load_json(os.path.join(BASE, ".claude.json")).get("mcpServers", {}))}
    for proj, cfg in load_json(os.path.join(BASE, ".claude.json")).get("projects", {}).items():
        if cfg.get("mcpServers"):
            servers.setdefault(os.path.basename(proj.rstrip("/\\")), []).extend(cfg["mcpServers"])
    for path in glob.glob(os.path.join(PROJECTS, "*", ".mcp.json")):
        proj = os.path.basename(os.path.dirname(path))
        servers.setdefault(proj, []).extend(load_json(path).get("mcpServers", {}))
    return {k: sorted(set(v)) for k, v in servers.items() if v}


def main_session(settings, agent_list):
    claude_md = os.path.join(BASE, "CLAUDE.md")
    md_lines = sum(1 for _ in open(claude_md, encoding="utf-8")) if os.path.exists(claude_md) else 0
    used = {s.removesuffix(" (on demand)") for a in agent_list for s in a[2]}
    own = [s for s in skills()[0] if s not in used]
    return {"model": settings.get("model", "default"),
            "detail": f"global CLAUDE.md {md_lines} lines · skills not given to an agent: {', '.join(own) or 'none'}"}


def infra(settings):
    """[(title, [(row, color)])] for the guardrails, extensions, MCP and slots."""
    perms = settings.get("permissions", {})
    guard = [f"ask: {r}" for r in perms.get("ask", [])] + [f"deny: {r}" for r in perms.get("deny", [])]
    hooks = [f"hook: {h}" for h in settings.get("hooks", {})]
    plugins = [p.split("@")[0] for p, on in settings.get("enabledPlugins", {}).items() if on]
    mods = [os.path.basename(m) for m in settings.get("env", {}).get("CLAUDE_CODE_PLUGIN_DIRS", "").split(";") if m]
    mcp = [f"{k}: {', '.join(v)}" for k, v in mcp_servers().items()]
    slots = [(f"{k}: {v.get('filler') or 'EMPTY'}", GREY if v.get("filler") else RED)
             for k, v in load_json(os.path.join(BASE, "slots.json")).items() if not k.startswith("_")]
    return [("Guardrails", [(r, GREY) for r in guard + hooks]),
            ("Plugins & mods", [(r, GREY) for r in plugins + [f"mod: {m}" for m in mods]]),
            ("MCP per project", [(r, GREY) for r in mcp]),
            ("Setup slots", slots)]


def table(main_info, agent_list, infra_cards):
    rows = [f"| **Main session** ({main_info['model']}) | {main_info['detail']} |"]
    for name, model, agent_skills, status, mcp in agent_list:
        parts = [", ".join(agent_skills)] + ([f"MCP: {', '.join(mcp)}"] if mcp else [])
        rows.append(f"| **{name}** ({model}{', draft' if status == 'draft' else ''}) | "
                    f"{' · '.join(p for p in parts if p) or '—'} |")
    rows += [f"| **{title}** | {' · '.join(r for r, _ in items)} |" for title, items in infra_cards]
    return "| Layer | What's there |\n|---|---|\n" + "\n".join(rows)


def main():
    settings = load_json(os.path.join(BASE, "settings.json"))
    agent_list = agents()
    main_info, infra_cards = main_session(settings, agent_list), infra(settings)
    with open(SVG, "w", encoding="utf-8") as f:
        f.write(setup_svg.render(main_info, agent_list, infra_cards))
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (f"---\ntags: [claude-code, setup, diagram]\n---\n\n# Setup\n\n"
            f"Generated from the live config at {stamp} by `.claude-config/scripts/setup_diagram.py` "
            f"(runs at every session start — don't edit by hand). "
            f"Decisions: [[Projects/Claude_Setup/Project|project note]].\n\n"
            f"![Setup diagram]({os.path.basename(SVG)})\n\n{table(main_info, agent_list, infra_cards)}\n")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(body)


if __name__ == "__main__":
    main()
