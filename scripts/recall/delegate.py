"""Delegation by hooks. Two cheap-model steps:
  input_step (slot `delegation-hook`): on his message -> what kind of response he wants (yes/no, full answer, task to say
  back, talk, confirmation, correction of the assistant) and the one instruction line for it.
  output_step (slot `delegation-gate`, off): before the reply -> did the turn skip a delegation the core rules require (tester, reviewer,
  knowledge-manager)?
The rules are read from CLAUDE.md at run time (the section "The core"), and the prompt wordings from
tasks/delegation-draft.md (fenced blocks and bullet lists), so editing either changes the behavior; nothing is copied
into the code. Both steps return (result, tokens) and raise on failure; the callers (hook.py, gate.py) fail open."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx, turnfacts, verdicts
import delegvet
from delegvet import veto

CLAUDE_MD = os.path.join(ctx.ROOT, "CLAUDE.md")
DRAFT = os.path.join(ctx.ROOT, "tasks", "delegation-draft.md")
SLOT = "delegation-gate"  # the output step; the input step runs under `delegation-hook`
INPUT_KINDS = ("QUESTION-YESNO", "QUESTION-OPEN", "TASK", "TALK", "CONFIRMATION", "CORRECTION")
LINE_KINDS = tuple(k for k in INPUT_KINDS if k != "CORRECTION")  # CORRECTION's line is capwrite.instruction
BLOCK_KINDS = ("TESTER", "TESTER-HERE", "REVIEWER", "KNOWLEDGE-MANAGER", "LOOP", "SETUP-MANAGER")


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
    """-> ([the one instruction line for his kind of message, plus the tests line for a task], tokens). One call also
    detects a correction (slot `capture`): that kind prints capture's write instruction and sets the owed marker."""
    import brain
    reply, tools = ctx.last_turn(transcript, prompt.strip()) if transcript else ("", [])
    recent = [l for l in (ctx.recent(transcript, 5) if transcript else []) if l != "Owner: " + prompt.strip()][-4:]
    recent = "\n".join(l[:600] for l in recent)  # his new message may already be in the transcript: left out
    prev = f"{recent}\n\nThe assistant's previous full reply:\n{reply[-4000:] or '(none)'}\nIts tool calls: {'; '.join(tools) or 'none'}"
    out, tok = brain.ask(_fill(_prompt("Input step"), prev=prev, prompt=prompt), tag="delegate-in")
    m = re.match(r"\W*([A-Z]+(?:-[A-Z]+)?)", out.upper())
    kind = m.group(1) if m else ""
    if kind not in INPUT_KINDS:
        return [], tok
    try:  # for the gate's context; a write failure must not lose the instruction
        __import__("gatectx").save_kind(transcript, prompt, kind)
    except OSError as e:
        ctx.log(f"delegate: kind not stored: {e!r}")
    lines = _lines("Instruction lines attached")
    rest = out.upper().partition("|" if kind == "CORRECTION" else kind)[2]
    extra = [lines[f] for f in ("DONE", "UNANSWERED") if re.search(r"\b" + f + r"\b", rest)]  # done -> SDD edit; ignored -> a no
    if kind == "CORRECTION":
        if not ctx.enabled("capture") or not reply.strip():
            return extra, tok
        import capwrite
        return [capwrite.instruction(out.partition("|")[2].strip() or "not specified", transcript, prompt)] + extra, tok
    return [lines[kind]] + ([lines["TESTS"]] if kind in ("TASK", "CONFIRMATION") else []) + extra, tok


def output_step(transcript, root=ctx.ROOT):
    """-> ((kind, reason) or None, tokens). kind: TESTER, REVIEWER, KNOWLEDGE-MANAGER, LOOP or SETUP-MANAGER."""
    import brain
    t = turnfacts.turn(transcript, root)
    if not t["text"].strip() and not t["tools"]:
        return None, 0
    if t["suite_unexcused"]:  # counted from the Bash calls, not asked of the brain: a tester call must come AFTER the run
        ctx.log("delegate: BLOCK TESTER-HERE: the main session ran a test suite itself")
        verdicts.log(transcript, "delegation", "BLOCK", "TESTER-HERE", features=delegvet.features(t))
        return ("TESTER-HERE", _lines("Block reasons")["TESTER-HERE"]), 0
    if not (t["edited"] or t["called"] or t["returned"] or t["claims"]):
        ctx.log("delegate: output call skipped: nothing edited, no agent called, nothing claimed")
        verdicts.log(transcript, "delegation", "OK", skip="nothing edited, called or claimed")
        return None, 0
    p = _fill(_prompt("Output step"), rules=rules(), human=t["human"], tools="\n".join(t["tools"]) or "(none)",
              text=t["text"], facts=t["facts"], max_rounds=str(turnfacts.ROUNDS_MAX))
    out, tok = brain.ask(p, tag="delegate-out")
    m = re.match(r"\s*BLOCK\s+([A-Z-]+)\s*\|?\s*(.*)", out, re.S)
    lead = _lines("Block reasons")
    if not (m and m.group(1) in lead):
        verdicts.log(transcript, "delegation", "OK", tokens=tok)
        return None, tok
    kind, reason = m.group(1), (m.group(2).strip().splitlines() or [""])[0]
    why = veto(kind, reason, t)
    if why:
        ctx.log(f"delegate: BLOCK {kind} dropped: {why} | {reason}")
        verdicts.log(transcript, "delegation", "BLOCK", kind, ctx.hedged(reason), dropped=why, tokens=tok, features=delegvet.features(t))
        return None, tok
    verdicts.log(transcript, "delegation", "BLOCK", kind, ctx.hedged(reason), tokens=tok, features=delegvet.features(t))
    return (kind, f"{lead[kind]} {reason}".strip()), tok


def check_sources():
    """[problem] when CLAUDE.md or the draft no longer parse the way the hooks read them (a renamed heading must fail
    loudly, not silently turn the delegation off). Run by `capture.py check`."""
    out = []
    for label, fn in (("CLAUDE.md section 'The core'", rules),
                      ("draft prompt 'Input step'", lambda: _need(_prompt("Input step"), ("prev", "prompt"))),
                      ("draft prompt 'Output step'", lambda: _need(_prompt("Output step"), ("rules", "human", "tools", "text",
                                                                                              "facts", "max_rounds"))),
                      ("draft 'Instruction lines attached'", lambda: _keys(_lines("Instruction lines attached"), LINE_KINDS + ("TESTS", "DONE", "UNANSWERED"))),
                      ("draft 'Block reasons'", lambda: _keys(_lines("Block reasons"), BLOCK_KINDS))):
        try:
            fn()
        except (ValueError, OSError) as e:
            out.append(f"{label}: {e}")
    return out


def _need(prompt, names):
    miss = [n for n in names if "{" + n + "}" not in prompt]
    if miss:
        raise ValueError("placeholder(s) missing: " + ", ".join(miss))


def _keys(lines, want):
    miss = [k for k in want if k not in lines]
    if miss:
        raise ValueError("bullet(s) missing: " + ", ".join(miss))
