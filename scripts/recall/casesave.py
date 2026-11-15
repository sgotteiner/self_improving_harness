"""Saving a captured case, and checking the cases: `capture.py approve <slug> <level>` moves a pending case into cases/
and runs every step the cases/README.md requires; `capture.py check` validates every case and also that CLAUDE.md and
the delegation draft still parse the way the hooks read them (a renamed heading must fail loudly)."""
import os, re

import ctx, delegate, diary, embed, history, index, mdfile, validate

PENDING = os.path.join(index.CASES, "_pending")
PROJECTS = os.path.dirname(ctx.ROOT)  # the folder that holds the work projects
INFERRED = "(inferred)"  # a why Claude inferred: it belongs in the flags file, never in his diary


def inferred_in(projects=None):
    """[diary path] of the setup's diary and of each work project's diary (named in its CLAUDE.md) that holds '(inferred)'."""
    projects = projects or PROJECTS
    dirs = [os.path.join(projects, f) for f in sorted(os.listdir(projects)) if os.path.isdir(os.path.join(projects, f))]
    paths = {diary.DIARY_SETUP if os.path.exists(diary.DIARY_SETUP) else "", *(diary.diary_for(d) for d in dirs)} - {""}
    return sorted(p for p in paths if INFERRED in mdfile.read(p))


def move(slug, level="advice"):
    """Move a pending case into cases/ with its level; drop source/his_words/status/asked (the words stay in history.db)."""
    src = os.path.join(PENDING, slug + ".md")
    dst = os.path.join(index.CASES, slug + ".md")
    if not os.path.exists(src):
        raise FileNotFoundError(f"no pending case {src}")
    if os.path.exists(dst):
        raise FileExistsError(f"{dst} already exists")
    if level not in validate.LEVELS:
        raise ValueError(f"level {level!r} is not one of {validate.LEVELS}")
    t = open(src, encoding="utf-8").read()
    t = re.sub(r"^(source|his_words|status|asked):.*\n", "", t, flags=re.M)
    t = re.sub(r"^level:.*$", "level: " + level, t, count=1, flags=re.M)
    open(dst, "w", encoding="utf-8", newline="").write(t)
    os.remove(src)
    return dst


def approve(slug, level="advice"):
    """Save a lesson as one complete step, in the order cases/README.md requires; every step is reported and a failed
    step is a failed approve (returns False). Steps: move, index, history (clean + publish occurrences),
    embeddings (encoded now, not at the first search), then the checks of validate.py (fields, privacy,
    occurrences, embeddings, recall rank). Examples are the written fields and the real cleaned occurrences, nothing
    generated. The case file stays in cases/ even when a step fails, so it can be fixed."""
    rep = []

    def step(name, fn):
        try:
            ok, ev = fn()
        except Exception as ex:
            ok, ev = False, f"error {ex!r}"
        rep.append((name, ok, ev))
        return ok

    dst = [None]

    def do_move():
        dst[0] = move(slug, level)
        return True, f"cases/{slug}.md, level {level}"

    def do_index():
        index.build()
        return index.meta(slug) is not None, f"{len(index.case_files())} cases indexed"

    def do_history():
        done, failed, files = history.sync()
        return failed == 0, f"{done} occurrences cleaned now, {failed} failed, {len(index.history_texts(slug))} for this case"

    def do_embed():
        d = index.parse(dst[0])
        t = validate.texts(d)
        embed.encode(t)
        return embed.missing(t) == 0, f"{len(t)} texts encoded and cached"

    if step("move", do_move):
        for name, fn in (("index", do_index), ("history", do_history), ("embeddings", do_embed)):
            if not step(name, fn):
                break
        else:
            rep += validate.run(dst[0], only=("fields", "privacy", "occurrences", "recall"))
    return _print(f"approve {slug} ({level})", rep)


def check_all(only=None):
    """Run the validation over every case in cases/ (or just `only`, with the evidence of every check).
    Also checks the delegation hooks' sources (delegate.check_sources). Returns True when all pass."""
    ok = True
    for problem in (delegate.check_sources() if not only else []):  # CLAUDE.md "The core" and the draft must still parse
        print("  [FAIL] delegation sources:", problem)
        ok = False
    for p in (inferred_in() if not only else []):
        print(f"  [FAIL] {p} holds '{INFERRED}': an inferred why belongs in the flags file, not in his diary")
        ok = False
    for f in index.case_files():
        if only and os.path.basename(f)[:-3] != only:
            continue
        ok &= _print(os.path.basename(f)[:-3], validate.run(f), quiet=not only)
    print("check:", "all cases pass" if ok else "FAILED")
    return bool(ok)


def _print(title, rep, quiet=False):
    allok = all(r[1] for r in rep)
    if not quiet or not allok:
        print(title + (": ok" if allok else ": FAILED"))
        for name, ok, ev in rep:
            if not quiet or not ok:
                print(f"  [{'ok' if ok else 'FAIL'}] {name}: {ev}")
    else:
        print(f"{title}: ok ({', '.join(n for n, _, _ in rep)})")
    return allok
