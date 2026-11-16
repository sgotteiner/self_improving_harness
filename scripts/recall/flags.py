"""Flags capture (switch `flags-capture` in slots.json). Agents report their own choices in their returns ("Choices beyond
the spec", "Decisions I made", ...). Those are Claude's record, not his design, so they belong in the project's flags file
(DIARY_FLAGS.md), never in his diary. On his next message (hook.py, last stage: it has the 300 s hook limit, the Stop hook
does not have room for a third brain call) every agent return of the transcript not seen before is matched cheaply by
heading/keyword; only a match costs one brain call, which extracts the choices as one-line items. Items go under a dated
`## Claude-on-its-own (<date>)` section, without asking him, except those that match a flag already in the file (embedding
>= ctx.SAME). What he asked is quoted from his own messages or "(not stated)". The setup's file is in the private vault; a
project's is next to its diary (diary.flags_for) and, being possibly public, is scrubbed with clean.violations."""
import datetime, hashlib, json, os, re, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, clean, ctx, diary, embed, grounding, mdfile, transcript

MARKERS = re.compile(r"choices beyond the spec|decisions i made|choices and gaps|decisions and placements|\(inferred\)|"
                     r"\(claude's\)|\b(?:my |own )?choices?\s*:|\bchoices? i made", re.I)
RETURNING = ("Agent", "Task", "SendMessage")  # tools whose result is an agent's return
HEADING = "## Claude-on-its-own ({date})"
BEFORE = r"^## Known debt"  # a new dated section goes above the debt list
MAX_ITEMS, MAX_ITEM_LEN = 8, 300  # per agent return, and characters of one item: a runaway reply cannot flood his flags file
MAX_RETURNS = 10  # agent returns read (one brain call each) per message; the rest wait for the next message
VAULT = os.path.dirname(os.path.dirname(os.path.dirname(diary.FLAGS_SETUP)))  # the private vault: Vault/Projects/<project>/<file>
STATE = os.path.join(tempfile.gettempdir(), "recall-flags")  # per session: hashes of the returns already read
EXTRACT = ("An AI agent returned this report to the assistant that started it:\n{text}\n\nThe report names choices the agent "
           "made on its own (beyond what the owner asked). List each choice as one line: <the mechanism chosen> | <what the "
           "owner actually asked, in his words if the report quotes them>. Only choices the report itself names; no personal "
           "data and no company names. Reply 'NONE' when it names none.")


def returns(tp):
    """[(hash, raw text)] of the agent returns in the transcript: results of Agent/SendMessage calls and notifications."""
    es = ctx.entries(tp)
    ids = {c["id"] for c in transcript.calls(es) if c["name"] in RETURNING}
    out = []
    for e in es:
        if e["type"] != "user":
            continue
        texts = [ctx._notice(e) or ""]
        for b in ctx.blocks(e):
            if b.get("type") == "tool_result" and b.get("tool_use_id") in ids:
                c = b.get("content")
                texts.append("\n".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else str(c or ""))
        out += [(hashlib.sha1(t.encode("utf-8")).hexdigest(), t) for t in texts if t.strip()]
    return out


def items_of(reply, messages):
    """['**mechanism** — owner asked: "his words"'] from the brain's lines `mechanism | what he asked`. What he asked is taken
    from his own messages (a span of them that the brain's text repeats), else '(not stated)': never the brain's guess."""
    out = []
    for l in reply.splitlines():
        what, _, asked = [x.strip(" -*`") for x in l.partition("|")]
        if what and what.upper() != "NONE" and len(out) < MAX_ITEMS:
            what = what[:MAX_ITEM_LEN]
            span = grounding.best_span(asked, messages)
            out.append(f"**{what}** — owner asked: " + (f'"{span}"' if span else "(not stated)"))
    return out


def private(path):
    """True for a file in the private vault; any other may be tracked in a public repo and is scrubbed."""
    return os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(os.path.abspath(VAULT)) + os.sep)


def _state(tp):
    return os.path.join(STATE, os.path.splitext(os.path.basename(tp))[0] + ".json")


def process(tp, ask=None):
    """Returns the flags lines appended (also [] when nothing new). `ask` replaces the brain in tests."""
    ask = ask or brain.ask
    path = diary.flags_for(diary.project_of(tp))
    if not path:
        ctx.log("flags: no flags file for this project")
        return []
    try:
        done = set(json.load(open(_state(tp), encoding="utf-8")))
    except (OSError, ValueError):
        done = set()
    known = {f"k{i}": [re.sub(r"[*`]", "", l[2:])] for i, l in enumerate(mdfile.read(path).splitlines()) if l.startswith("- ")}
    mine = [ctx.human_text(e) for e in ctx.entries(tp) if ctx.human_text(e)]
    new, read = [], 0
    for h, r in returns(tp):
        if h in done or not MARKERS.search(r):
            continue
        if read >= MAX_RETURNS or ctx.over_budget("flags-extract"):
            break  # not marked as read: the next message continues
        read += 1
        try:
            items = items_of(ask(EXTRACT.format(text=r), tag="flags-extract")[0], mine)
            for item in items:
                plain = re.sub(r"[*`]", "", item)
                if not private(path) and clean.violations(plain):
                    ctx.log("flags: item dropped, the file may be public and the item names something private")
                elif known and max(embed.scores(plain, known).values()) >= ctx.SAME:
                    ctx.log("flags: skipped, matches a flag already recorded")
                else:
                    known[f"n{len(known)}"] = [plain]
                    new.append("- " + item)
            done.add(h)
        except Exception as e:  # one failing return must not lose the others
            ctx.log(f"flags: a return was skipped: {e!r}")
    if new:
        text = mdfile.read(path)  # read again right before the write: the file may have changed during the brain calls
        head = HEADING.format(date=datetime.date.today())
        mdfile.write_atomic(path, mdfile.insert_under(text, head, "\n".join(new), new_before=BEFORE))
    os.makedirs(STATE, exist_ok=True)  # only after the write: a failed write leaves the returns unread, the next message retries
    json.dump(sorted(done), open(_state(tp), "w", encoding="utf-8"))
    return new
