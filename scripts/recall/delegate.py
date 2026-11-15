"""Delegation by hooks (switch `delegation-hook` in slots.json, default off). Two cheap-model steps:
  input_step: on his message -> which delegation it calls for (knowledge-manager, test, implementer), if any.
  output_step: before the reply -> did the turn skip a delegation the core rules require (tester, reviewer,
  knowledge-manager)?
The rules are read from CLAUDE.md at run time (the section "The core"), and the prompt wordings from
tasks/delegation-draft.md (fenced blocks and bullet lists), so editing either changes the behavior; nothing is copied
into the code. Both steps return (result, tokens) and raise on failure; the callers (hook.py, gate.py) fail open."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

CLAUDE_MD = os.path.join(ctx.ROOT, "CLAUDE.md")
DRAFT = os.path.join(ctx.ROOT, "tasks", "delegation-draft.md")
SLOT = "delegation-hook"


def rules():
    """The core section of CLAUDE.md, from its heading up to the next `## ` heading."""
    t = open(CLAUDE_MD, encoding="utf-8").read()
    m = re.search(r"^## The core.*?(?=^## )", t, re.S | re.M)
    if not m:
        raise ValueError("section 'The core' not found in CLAUDE.md")
    return m.group(0).strip()


def _draft():
    return open(DRAFT, encoding="utf-8").read()


def _prompt(heading):
    """The fenced text block under `## <heading...>` in the draft."""
    m = re.search(r"^## " + re.escape(heading) + r".*?```text\n(.*?)```", _draft(), re.S | re.M)
    if not m:
        raise ValueError(f"prompt '{heading}' not found in {DRAFT}")
    return m.group(1).strip()


def _lines(after):
    """{KEY: text} from the bullet list `- KEY: text` that follows the line starting with `after`."""
    t = _draft()
    i = t.index(after)
    out = {}
    for l in t[i:].splitlines()[1:]:
        m = re.match(r"- ([A-Z-]+): (.*)", l)
        if m:
            out[m.group(1)] = m.group(2)
        elif out and not l.strip():
            break
    return out


def _fill(template, **kw):
    for k, v in kw.items():  # plain replace: the rules and messages contain braces and must not be format()ed
        template = template.replace("{" + k + "}", v)
    return template


def input_step(prompt, transcript):
    """-> ([instruction lines to attach], tokens)."""
    import brain
    p = _fill(_prompt("Input step"), rules=rules(), ctx="\n".join(ctx.recent(transcript, 4)) if transcript else "(none)",
              prompt=prompt)
    out, tok = brain.ask(p, tag="delegate-in")
    lines = _lines("Instruction lines attached")
    res = []
    for l in out.splitlines()[:2]:
        kind, _, why = [x.strip(" -*`") for x in l.partition("|")]
        if kind in lines:
            res.append(lines[kind] + (f" Context: {why}" if why else ""))
    return res, tok


SETUP_PATHS = ("CLAUDE.md", "settings.json", "slots.json", "agents/", "skills/", "scripts/", "cases/", "mods/")
SETUP_SKIP = ("cases/_pending/", "tasks/todo.md")  # drafts waiting for him and the to-do list alone do not count


def setup_rel(path):
    """Path relative to the setup root if it is a setup file that counts, else None."""
    if not path:
        return None
    p = os.path.normpath(path.replace("/c/", "C:/", 1) if path.startswith("/c/") else path)
    root = os.path.normpath(ctx.ROOT)
    if os.path.normcase(p).startswith(os.path.normcase(root) + os.sep):
        rel = p[len(root) + 1:].replace(os.sep, "/")
        if rel.startswith(SETUP_SKIP) or rel in SETUP_SKIP:
            return None
        if rel in SETUP_PATHS or rel.startswith(SETUP_PATHS):
            return rel
    return None


def turn(transcript):
    """(his latest message, assistant final text, tool lines with the change and agent results shown, facts).
    The window is everything since his latest message. The facts are counted from the transcript, not remembered: the
    order of implementer/tester agent calls (the loop's rounds) and the setup files edited."""
    es = ctx.entries(transcript)
    human = [ctx.human_text(e) for e in es if ctx.human_text(e)]
    text, _ = ctx.last_turn(transcript)
    start = ctx._start(es, None)
    results = {}
    for e in es[start:]:
        if e["type"] == "user":
            for b in ctx.blocks(e):
                if b.get("type") == "tool_result":
                    c = b.get("content")
                    c = " ".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else str(c or "")
                    results[b.get("tool_use_id")] = re.sub(r"\s+", " ", c)[:600]
    tools, order, setup, sm = [], [], [], False
    for e in es[start:]:
        if e["type"] != "assistant":
            continue
        for b in ctx.blocks(e):
            if b.get("type") != "tool_use":
                continue
            i = b.get("input", {})
            res = results.get(b.get("id"))
            if b["name"] in ("Edit", "MultiEdit", "Write", "NotebookEdit"):
                new = i.get("new_string") or i.get("content") or str(i.get("edits", ""))
                old = i.get("old_string", "")
                tools.append(f"{b['name']} {i.get('file_path', '')}: {old[:200]!r} -> {new[:300]!r}")
                rel = setup_rel(i.get("file_path", ""))
                if rel and rel not in setup:
                    setup.append(rel)
            elif b["name"] in ("Agent", "Task"):
                kind = str(i.get("subagent_type", ""))
                tools.append(f"{b['name']} agent={kind}: {str(i.get('description') or i.get('prompt', ''))[:200]}"
                             + (f" || RESULT: {res[:500]}" if res else ""))
                if "implementer" in kind:
                    order.append("IMPLEMENTER")
                elif "tester" in kind:
                    order.append("TESTER")
                sm = sm or kind == "setup-manager"
            else:
                tools.append(ctx.tool_line(b)[:300] + (f" || RESULT: {res[:300]}" if res else ""))
    rounds, open_round = 0, False  # a round = an implementer call followed by a tester call
    for x in order:
        if x == "IMPLEMENTER":
            open_round = True
        elif open_round:
            rounds, open_round = rounds + 1, False
    facts = ("Agent calls since his latest message, in order: " + (", ".join(order) or "none") +
             f". Completed implementer-to-tester rounds: {rounds}. Implementer calls: {order.count('IMPLEMENTER')}.\n"
             "Setup files edited since his latest message (not counting pending drafts or the to-do list): " +
             (", ".join(setup) or "none") + f". Setup-manager agent called: {'yes' if sm else 'no'}.")
    return (human[-1] if human else ""), text, tools, facts


def output_step(transcript):
    """-> ((kind, reason) or None, tokens). kind: TESTER, REVIEWER, KNOWLEDGE-MANAGER, LOOP or SETUP-MANAGER."""
    import brain
    human, text, tools, facts = turn(transcript)
    if not text.strip() and not tools:
        return None, 0
    p = _fill(_prompt("Output step"), rules=rules(), human=human, tools="\n".join(tools) or "(none)", text=text,
              facts=facts)
    out, tok = brain.ask(p, tag="delegate-out")
    m = re.match(r"\s*BLOCK\s+([A-Z-]+)\s*\|?\s*(.*)", out, re.S)
    lead = _lines("Block reasons")
    if m and m.group(1) in lead:
        return (m.group(1), f"{lead[m.group(1)]} {m.group(2).strip().splitlines()[0] if m.group(2).strip() else ''}".strip()), tok
    return None, tok
