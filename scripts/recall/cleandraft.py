"""The cheap-model calls of cleanup.py: draft a reword, group lessons of the same kind (one call over all of them), and check a
wording (separate calls): against the lessons it replaces, each with its Right action, and the KIND of mistake of their active
situations; for a merge also each lesson alone against the wording. Raises when a call fails.
Usage: python -I scripts/recall/cleandraft.py eval   (real calls on the labelled merge cases in cleandraft_eval.jsonl)"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, clean, relevance

REWORD = ("A lesson an AI coding assistant learned from its mistakes:\n{lesson}\nRight: {right}\n\nProblem: {why}\nReal situations "
          "behind it:\n{sits}\n\nReword the lesson as ONE general sentence that fixes the problem and still covers every kind of "
          "mistake above. No names, paths or file names. Reply with the sentence only.")
MERGE = ("Lessons of an AI coding assistant (id: lesson. Right: what to do instead):\n{lessons}\n\nFind groups of two or more "
         "lessons that are the SAME kind of mistake: one general sentence would cover them, and following it means doing the same "
         "thing. Lessons whose Right actions differ are not the same kind, even when they share a topic: do not look for overlap "
         "that is not there. For each group reply with one line: `MERGE <id>,<id> | <ONE general sentence that covers all of "
         "them>`. Reply `NONE` when no lessons are the same kind.")
CHECK = ("A lesson's new wording: {text}\n\nThe lessons it replaces (id: lesson. Right: what to do instead):\n{sources}\n\nThe "
         "kinds of mistake it must cover (real situations; judge the KIND of mistake, not the exact words):\n{sits}\n\nCheck: "
         "(1) is each Right above a direct instance of the one new sentence, i.e. doing the Right is doing what the sentence says "
         "(a Right may be more specific; who performs the action and the exact commands do not matter, only WHAT is done)? FAIL when the sentence has an `or` joining two different actions to choose between, or "
         "doing it takes two different actions; saying plainly that the action was not done is not a second action. (2) Does it still cover the kind of mistake of EVERY "
         "situation, without becoming empty or vague? Reply `<1-5> | OK` or `<1-5> | FAIL | <which lesson or situation, why>`; the score is how sure you are that the wording is acceptable (5 = certain, 3 = doubtful).")
PAIR = ("A lesson's new wording: {text}\n\nOne lesson it replaces: {lesson}\nRight: {right}\n\nIs that lesson's Right a direct "
        "instance of the new wording (doing that Right is doing what the new wording says; the Right may be more specific; who performs it does not matter; the "
        "wording must not need a different action or an `or` between two different actions)? Reply `<1-5> | OK` or `<1-5> | FAIL | <why>`; the score is how sure you are that it is acceptable (5 = certain, 3 = doubtful).")
MERGE_LINE = re.compile(r"MERGE\s+([^|]+?)\s*\|\s*(.+)", re.I)


def _bullets(rows):
    return "\n".join(f"- {r['situation']}" for r in rows) or "- (none)"


def reword(lesson, right, why, sits, extra=()):
    """The new wording of a lesson (one line). sits = its active situations; extra = texts of cases that matched none of them."""
    out, _ = brain.ask(REWORD.format(lesson=lesson, right=right, why=why,
                                     sits=_bullets(sits) + "".join(f"\n- {e}" for e in extra)), tag="cleanup-reword")
    return (out.strip().splitlines() or [""])[0].strip(" `\"")


def merges(ls):
    """[(ids, wording)] groups of same-kind lessons, from one call over all of them; ids are known lessons only."""
    out, _ = brain.ask(MERGE.format(lessons="\n".join(f"- {c}: {l} Right: {r}" for c, (_, l, r) in ls.items())), tag="cleanup-merge")
    found = []
    for line in out.splitlines():
        m = MERGE_LINE.search(line)
        ids = [i.strip(" `*") for i in m.group(1).split(",")] if m else []
        if len(ids) > 1 and all(i in ls for i in ids) and len(set(ids)) == len(ids):
            found.append((ids, m.group(2).strip(" `")))
    return found


def _ok(prompt, tag):
    """"" when the model answered OK with a score of RELEVANCE_MIN or above, else its FAIL text (an unreadable answer, a missing
    score or a doubtful one is a fail: a merge not proposed now comes back at the next run)."""
    out, _ = brain.ask(prompt, tag=tag)
    score, rest = relevance.split(out.strip(" `*"))
    rest = rest.strip(" `*")
    if not rest.upper().startswith("OK"):
        return rest or "empty answer"
    return "" if score is not None and score >= relevance.RELEVANCE_MIN else f"not sure enough ({score}): {out[:150]}"


def why_not(text, sources, sits):
    """"" when the wording is acceptable, else why not. sources = [(id, lesson, right)] of the lessons it replaces; sits = their
    active situations. No privacy hit; one call (CHECK) on all sources and situations; then, when there are several sources,
    one call (PAIR) per source: that lesson alone against the wording."""
    if not text or clean.violations(text, strict=True):
        return "empty or private text"
    if not sources and not sits:
        return ""
    src = "\n".join(f"- {i}: {l} Right: {r}" for i, l, r in sources) or "- (none)"
    bad = _ok(CHECK.format(text=text, sources=src, sits=_bullets(sits)), "cleanup-check")
    for i, l, r in sources if len(sources) > 1 else ():
        if bad:
            break
        why = _ok(PAIR.format(text=text, lesson=l, right=r), "cleanup-pair")
        bad = f"{i}: {why}" if why else ""
    return bad


def passes(text, sources, sits):
    return not why_not(text, sources, sits)


if __name__ == "__main__" and sys.argv[1:] == ["eval"]:
    import cleaneval
    sys.exit(cleaneval.main())
