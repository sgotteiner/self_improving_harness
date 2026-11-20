"""What the turn did, counted from the transcript and the setup's git state, not remembered: the agents called or resumed
(a SendMessage to an agent counts as calling its type), the order of implementer/tester calls (the loop's rounds), the
setup files edited and whether the setup-manager was called AFTER the edit, background agents still running, whether
anything was edited or claimed. delegate.py hands these to the cheap model and uses them to veto its verdict."""
import re

import ctx, setupstate, suitecmd, transcript
from setupstate import EDIT_TOOLS

TYPES = ("implementer", "tester", "reviewer", "knowledge-manager", "setup-manager")  # matched by substring
BASH_WRITE = re.compile(r"(>|\btee\b|\bsed\s+-i|\b(mv|cp|rm|mkdir|touch|curl|npm|pip|python|node)\b|\bgit\s+(commit|add|checkout|"
                        r"reset|merge|rebase|push|apply)\b|Out-File|Set-Content)")  # a Bash call that may write files
CLAIMS = re.compile(r"\b(done|finished|fixed|complete[d]?|(it|that|this) works(?!\s+(with|for|on|in|like|by))|works now|now works|is working|now working|passes|passed|saved|updated|added|implemented|"
                    r"committed|ready)\b", re.I)  # the final message claims something is done
PROGRESS = re.compile(r"\b(still|not yet|waiting|until|once|when|then|will|going to|about to|building|running|in progress|"
                      r"working on|after|before|if|come back|report)\b", re.I)  # a sentence about work under way is no claim
ROUNDS_MAX = 2  # core rule 1: the implementer -> tester loop runs at most this many rounds (a round = both calls)


def claims(text):
    """True when a sentence of the final message claims something is done; "still building ... then the reviewer" does not."""
    lines = [l for l in text.splitlines() if not l.lstrip().startswith(">")]  # a quoted draft ("> ...") is not a claim about the work
    return any(CLAIMS.search(x) and not PROGRESS.search(x) for x in re.split(r"(?<=[.!?:;])\s+|\n+", "\n".join(lines)))


def _kinds(kind):
    return [t for t in TYPES if t in kind]


def _launched(c, types):
    """(id, type) of the background agent an Agent/Task/SendMessage call started or resumed, else (None, kind)."""
    n, i, res, to = c["name"], c["input"], c["result"], str(c["input"].get("to", ""))
    kind = str(i.get("subagent_type", "")) if n != "SendMessage" else types.get(to, to)
    m = transcript.AGENT_ID.search(res)
    aid = m.group(1) if n != "SendMessage" and m and "Async agent launched" in res else (to if to in types else None)
    if not aid and n != "SendMessage" and i.get("run_in_background"):  # launched, its result not (yet) in the usual form
        aid = c["id"]
    return aid, kind


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
    suite_seq, tester_seqs, impl_seqs, fell, reviews = -1, [], [], [], []  # the suite run, tester calls/results, implementer calls, results, reviews
    rets, commits = [], []  # (agent type, result) of agents that returned this turn; the outputs of `git commit` calls (feature traces)
    hs = [i for i, e in enumerate(es) if ctx.human_text(e)]
    horizon = hs[-3] * transcript.SEQ if len(hs) >= 3 else 0  # an agent started in the last three turns and not returned is still running
    for c in (c for c in cs if c["name"] in ("Agent", "Task", "SendMessage") and c["seq"] >= horizon):
        aid, kind = _launched(c, types)
        if aid:
            pend[aid] = (c["seq"], kind, c["id"])
    for s, txt in ns:  # a result that came back (in this turn or an earlier one) ends the wait
        m, tid = transcript.TASK_ID.search(txt), transcript.TOOL_ID.search(txt)
        for k in [k for k, v in pend.items() if s > v[0] and ((m and m.group(1) == k) or (tid and tid.group(1) == v[2]))]:
            del pend[k]
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
                tester_seqs += [c["seq"]] if k == "tester" else []
                impl_seqs += [c["seq"]] if k == "implementer" else []
                fell += [(c["seq"], res)] if k == "tester" else []
                reviews += [(c["seq"], res)] if k == "reviewer" and res else []
            order += [k.upper() for k in _kinds(kind) if k in ("implementer", "tester")]
            if not _launched(c, types)[0] and res:
                t["returned"] = True
                rets.append((kind, res))
        else:
            t["tools"].append(ctx.tool_line({"name": n, "input": i}) + tail)
            if n == "Bash" and suitecmd.is_suite(str(i.get("command", ""))):
                suite_seq = c["seq"]
                fell.append((c["seq"], res))
            if n == "Bash" and res and re.search(r"\bgit\s+commit\b", str(i.get("command", ""))):
                commits.append(res)
            if n == "Bash" and BASH_WRITE.search(str(i.get("command", ""))):
                t["edited"] = True
                bash_seqs.append(c["seq"])
    for s, txt in (n for n in ns if n[0] >= start):
        t["returned"] = True
        m, tid = transcript.TASK_ID.search(txt), transcript.TOOL_ID.search(txt)
        kind = types.get(tid.group(1) if tid else "") or types.get(m.group(1) if m else "") or ""
        called += [k for k in _kinds(kind) if k not in called]  # its result arrived this turn: that agent's work counts now
        tester_seqs += [s] if "tester" in kind else []
        fell += [(s, txt)] if "tester" in kind else []
        reviews += [(s, txt)] if "reviewer" in kind else []
        rets.append((kind or "agent", txt))
        t["tools"].append(f"Background agent ({kind or 'unknown type'}) result received this turn: {txt}")
    changed = setupstate.git_changed(tp, root)
    setup += [r for r in changed if r not in setup]
    t["edited"] = t["edited"] or bool(changed)
    fseqs = [s for s, x in fell if suitecmd.FELL.search(x)]
    last_edit = max(edit_seqs + (bash_seqs if changed else []), default=-1)
    t.update(rets=rets, commits=commits, setup=setup, called=called, claims=claims(t["text"]), pending=[v[1] for v in pend.values()],
             sm_ok=not setup or any(s > last_edit for s in sm_seqs),
             suite_unexcused=suite_seq >= 0 and not any(s > suite_seq for s in tester_seqs),  # a suite run needs a tester call AFTER it
             fell_short=bool(fseqs),  # a test or tester result of this turn says the purpose fell short
             round_started=bool(fseqs) and any(e > max(fseqs) for e in impl_seqs),  # an implementer call or resume came after that result
             review_open=any(suitecmd.FIXES.search(x) and not any(e > s for e in edit_seqs + impl_seqs) for s, x in reviews))
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
