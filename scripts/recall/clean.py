"""Privacy: one place that knows what must never reach the public repo, and how to rewrite an occurrence into
a short structured example. Used by validate.py (check of the human-written fields of a case) and history.py (cleaning
of each recorded occurrence). The brain rewrites; a deterministic scan then has the last word, and an occurrence that
still fails is not stored (fail closed)."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# the folder that holds the work projects is the parent of this harness folder
PROJECTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
# extra names that are not folder names (companies, products): one per line in a local, gitignored file, so the public
# repo never lists them
LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "denylist.local.txt")
try:
    KNOWN = [l.strip() for l in open(LOCAL, encoding="utf-8") if l.strip() and not l.startswith("#")]
except OSError:
    KNOWN = []
# words that are part of a project folder name but are ordinary vocabulary, so they are not names by themselves
GENERIC = set("""agents agent personal videos video vault trading projects project feature knowledge management indicators
indicator setup experience summarizer channel groups group reliable telegram crypto copy augmentation form test
transcriptor config claude work youtube formaugmentation""".split())
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ABS = re.compile(r"(?<![\w])[A-Za-z]:[\\/]|(?<![\w:.])/(?:c|d|e|users|home|mnt|tmp)/|\\\\|~[\\/]", re.I)
_REL = re.compile(r"[\w.-]+[\\/][\w./\\-]*\w\.\w{1,5}\b|\b\w[\w-]*\.(?:py|md|js|ts|json|html|jsonl|db|yml|yaml|sh|ps1)\b")
_SESSION = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\b[0-9a-f]{20,}\b", re.I)


def denylist():
    """Lowercase names that must not appear: the folders under the projects directory (whole, and each part that is
    not ordinary vocabulary) plus the known company/product names."""
    names = {k.lower() for k in KNOWN}
    try:
        folders = [f for f in os.listdir(PROJECTS) if os.path.isdir(os.path.join(PROJECTS, f)) and not f.startswith(".")]
    except OSError:
        folders = []
    for f in folders:
        whole = f.lower()
        if whole not in GENERIC and len(whole) >= 5:
            names.add(whole)
        for part in re.split(r"[_\-\s.]+", whole):
            if len(part) >= 5 and part not in GENERIC:
                names.add(part)
    return sorted(names)


_DENY = None


def violations(text, strict=False):
    """List of problems found in a text. strict adds relative file paths, file names and session ids (for cleaned
    occurrences); the default is for the human-written case fields, which may name harness files."""
    global _DENY
    if _DENY is None:
        _DENY = denylist()
    t = text or ""
    out = [f"email {m.group(0)!r}" for m in _EMAIL.finditer(t)]
    out += [f"path {m.group(0)!r}" for m in _ABS.finditer(t)]
    low = t.lower()
    out += [f"name {n!r}" for n in _DENY if n in low]
    if strict:
        out += [f"file {m.group(0)!r}" for m in _REL.finditer(t)]
        out += [f"session id {m.group(0)[:8]}..." for m in _SESSION.finditer(t)]
    return out


PROMPT = """Below is one real occurrence of a mistake of an AI coding assistant, to be stored as a short, general example
in a public lesson file. Reply with JSON only: {{"situation": "...", "assistant_did": "...", "disliked": "..."}}
- situation: what was going on when it happened (one sentence).
- assistant_did: what the assistant did or said (one sentence).
- disliked: what the owner did not like, in his own manner of speaking but in general words (one sentence; if the
  text is a check's reason, what the check found wrong).
Each part is complete but short (max 30 words). Use only what the material says; if a part is not in it, infer it
from the lesson and the other parts without inventing details. Remove or replace with a generic description: company,
product and tool names, project names, file names and paths, people, session ids, identifying numbers, code.

The lesson this occurrence belongs to: {lesson}
Kind: {kind}
Text:
{text}
{context}"""
KIND = {"correction": "the owner's own words correcting the assistant",
        "gate": "a reason given by an automatic check that stopped the assistant's reply"}
PARTS = ("situation", "assistant_did", "disliked")


def _context(source, text, transcript):
    """What the assistant did just before his correction, from the transcript if it is still on disk."""
    if source != "correction" or not transcript or not os.path.exists(transcript):
        return ""
    try:
        import ctx
        prev, tools = ctx.last_turn(transcript, text.strip())
    except Exception:
        return ""
    if not prev.strip():
        return ""
    return "The assistant's turn before his words:\n" + prev[:1500] + "\nTool calls: " + "; ".join(tools)[:500]


def clean(text, source, lesson="", transcript=""):
    """Return {situation, assistant_did, disliked} (short, every part present) or None when the brain failed or a
    part still fails the strict scan."""
    import brain
    note = ""
    ctxt = _context(source, text, transcript)
    for _ in range(2):
        out, _t = brain.ask(PROMPT.format(lesson=lesson or "(not given)", kind=KIND.get(source, source), text=text,
                                          context=ctxt) + note, tag="clean")
        m = re.search(r"\{.*\}", out, re.S)
        try:
            d = json.loads(m.group(0)) if m else {}
        except ValueError:
            d = {}
        d = {k: re.sub(r"\s+", " ", str(d.get(k, ""))).strip() for k in PARTS}
        bad = [f"{k}: {v}" for k in PARTS for v in violations(d[k], strict=True)]
        short = [k for k in PARTS if not 8 <= len(d[k]) <= 300]
        if not bad and not short:
            return d
        note = ("\n\nYour previous reply was rejected: " + "; ".join(bad[:4]) + "." if bad else "\n\nYour previous reply was rejected.") \
            + (" Missing or unusable parts: " + ", ".join(short) + "." if short else "") + " Reply again."
    return None


if __name__ == "__main__":
    print(denylist())
