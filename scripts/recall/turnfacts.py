"""What the turn did, counted from the transcript and the setup's git state, not remembered: the agents called or resumed
(a SendMessage to an agent counts as calling its type), the order of implementer/tester calls (the loop's rounds), the
setup files edited and whether the setup-manager was called AFTER the edit, background agents still running, whether
anything was edited or claimed. delegate.py hands these to the cheap model and uses them to veto its verdict."""
import re

import ctx, setupstate, transcript
from setupstate import EDIT_TOOLS

TYPES = ("implementer", "tester", "reviewer", "knowledge-manager", "setup-manager")  # matched by substring
BASH_WRITE = re.compile(r"(>|\btee\b|\bsed\s+-i|\b(mv|cp|rm|mkdir|touch|curl|npm|pip|python|node)\b|\bgit\s+(commit|add|checkout|"
                        r"reset|merge|rebase|push|apply)\b|Out-File|Set-Content)")  # a Bash call that may write files
CLAIMS = re.compile(r"\b(done|finished|fixed|complete[d]?|works|working|passes|passed|saved|updated|added|implemented|"
                    r"committed|ready)\b", re.I)  # the final message claims something is done
ROUNDS_MAX = 2  # core rule 1: the implementer -> tester loop runs at most this many rounds (a round = both calls)


def _kinds(kind):
    return [t for t in TYPES if t in kind]


def turn(tp, root=ctx.ROOT):
    """dict: human, text, tools (lines for the brain), facts (text), edited, claims, called (type names), pending (types of
    background agents still running), setup (files edited), sm_ok, returned (an agent result came back this turn)."""
    es = ctx.entries(tp)
    human = [ctx.human_text(e) for e in es if ctx.human_text(e)]
    start = ctx._start(es, None) * transcript.SEQ
    cs, ns = transcript.calls(es), transcript.notices(es)
    types = transcript.agent_types(cs, ns)
    t = dict(human=human[-1] if human else "", text=ctx.last_turn(tp)[0], tools=[], edited=False, returned=False)
    order, called, pend, setup, edit_seqs, bash_seqs, sm_seqs = [], [], {}, [], [], [], []
    for c in (c for c in cs if c["seq"] >= start):
        n, i, res = c["name"], c["input"], c["result"]
        tail = f" || RESULT: {res}" if res else ""
        if n in EDIT_TOOLS:
            new = i.get("new_string") or i.get("content") or str(i.get("edits", ""))
            t["tools"].append(f"{n} {i.get('file_path', '')}: {i.get('old_string', '')!r} -> {new!r}")
            t["edited"] = True
            rel = setupstate.setup_rel(i.get("file_path", ""), root)
            if rel:
                edit_seqs.append(c["seq"])
                setup += [rel] if rel not in setup else []
        elif n in ("Agent", "Task", "SendMessage"):
            to = str(i.get("to", ""))
            kind = str(i.get("subagent_type", "")) if n != "SendMessage" else types.get(to, to)
            label = f"{n} agent={kind}" if n != "SendMessage" else f"SendMessage to {kind} agent (resumed)"
            t["tools"].append(f"{label}: {i.get('description') or i.get('summary') or i.get('prompt', '')}{tail}")
            for k in _kinds(kind):
                called.append(k)
                sm_seqs += [c["seq"]] if k == "setup-manager" else []
            order += [k.upper() for k in _kinds(kind) if k in ("implementer", "tester")]
            m = transcript.AGENT_ID.search(res)
            aid = m.group(1) if n != "SendMessage" and m and "Async agent launched" in res else (to if to in types else None)
            if aid:
                pend[aid] = (c["seq"], kind)
            elif res:
                t["returned"] = True
        else:
            t["tools"].append(ctx.tool_line({"name": n, "input": i}) + tail)
            if n == "Bash" and BASH_WRITE.search(str(i.get("command", ""))):
                t["edited"] = True
                bash_seqs.append(c["seq"])
    for s, txt in (n for n in ns if n[0] >= start):
        t["returned"] = True
        m = transcript.TASK_ID.search(txt)
        if m and m.group(1) in pend and s > pend[m.group(1)][0]:
            del pend[m.group(1)]
    changed = setupstate.git_changed(tp, root)
    setup += [r for r in changed if r not in setup]
    t["edited"] = t["edited"] or bool(changed)
    last_edit = max(edit_seqs + (bash_seqs if changed else []), default=-1)
    t.update(setup=setup, called=called, claims=bool(CLAIMS.search(t["text"])), pending=[k for _, k in pend.values()],
             sm_ok=not setup or any(s > last_edit for s in sm_seqs))
    rounds, open_round = 0, False  # a round = an implementer call followed by a tester call
    for x in order:
        if x == "IMPLEMENTER":
            open_round = True
        elif open_round:
            rounds, open_round = rounds + 1, False
    t["facts"] = (f"Agent calls since his latest message (a resumed agent counts), in order: {', '.join(order) or 'none'}. "
                  f"Completed implementer-to-tester rounds: {rounds} of at most {ROUNDS_MAX}. Implementer calls: {order.count('IMPLEMENTER')}.\n"
                  f"Agent types called or resumed this turn: {', '.join(sorted(set(called))) or 'none'}.\n"
                  "Setup files edited since his latest message (not counting pending drafts, generated files or the to-do list): "
                  f"{', '.join(setup) or 'none'}. Setup-manager called after the edit: {'yes' if t['sm_ok'] and 'setup-manager' in called else 'no'}.\n"
                  "Background agents started or resumed this turn that have not returned yet: "
                  f"{', '.join(t['pending']) or 'none'}.")
    return t
