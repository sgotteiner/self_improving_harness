"""Tool calls of a transcript with their results, and background-agent notifications, in order. Shared by the
delegation hooks (turnfacts.py) and flags capture (flags.py). A position `seq` = entry index * SEQ + block index, so a
call and a notification can be ordered. Results are kept whole (no size caps)."""
import re

import ctx

SEQ = 1000
AGENT_ID = re.compile(r"agentId: (\w+)")
TASK_ID = re.compile(r"<task-id>(.*?)</task-id>")
TOOL_ID = re.compile(r"<tool-use-id>(.*?)</tool-use-id>")


def flat(content):
    c = " ".join(x.get("text", "") for x in content if isinstance(x, dict)) if isinstance(content, list) else str(content or "")
    return re.sub(r"\s+", " ", c)


def calls(es):
    """[{seq, name, input, id, result}] for every assistant tool call, in order."""
    results = {}
    for e in es:
        if e["type"] == "user":
            for b in ctx.blocks(e):
                if b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = flat(b.get("content"))
    return [{"seq": i * SEQ + j, "name": b["name"], "input": b.get("input", {}), "id": b.get("id"),
             "result": results.get(b.get("id"), "")}
            for i, e in enumerate(es) if e["type"] == "assistant"
            for j, b in enumerate(ctx.blocks(e)) if b.get("type") == "tool_use"]


def notices(es):
    """[(seq, text)] for every background-agent notification entry."""
    return [(i * SEQ, ctx._notice(e)) for i, e in enumerate(es) if ctx._notice(e)]


def running(es):
    """[(agent type, description)] of the background agents launched in these entries with no completion notification yet."""
    cs, ns = calls(es), notices(es)
    types, out = agent_types(cs, ns), {}
    for c in cs:
        m = AGENT_ID.search(c["result"])
        if c["name"] in ("Agent", "Task") and m and "Async agent launched" in c["result"]:
            out[m.group(1)] = (c["id"], types.get(m.group(1), "agent"), str(c["input"].get("description", "")))
    for _, t in ns:
        a, b = TASK_ID.search(t), TOOL_ID.search(t)
        for k in [k for k, v in out.items() if (a and a.group(1) == k) or (b and b.group(1) == v[0])]:
            del out[k]
    return [(v[1], v[2]) for v in out.values()]


def agent_types(cs, ns):
    """{agent id or tool-use id: subagent type} from the Agent calls (the id is in the launch result and in the
    notification), so a SendMessage that resumes an agent can be mapped back to the type that was started."""
    out = {}
    for c in cs:
        if c["name"] in ("Agent", "Task"):
            kind = str(c["input"].get("subagent_type", ""))
            out[c["id"]] = kind
            m = AGENT_ID.search(c["result"])
            if m:
                out[m.group(1)] = kind
    for _, t in ns:
        a, b = TASK_ID.search(t), TOOL_ID.search(t)
        if a and b and b.group(1) in out:
            out[a.group(1)] = out[b.group(1)]
    return out
