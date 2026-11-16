"""Repeatable eval of decision capture's detector (decisions.DETECT) on real messages of the owner, labelled by hand and
cleaned (no company or project names: this repo is public). Run it after changing the DETECT prompt and compare:
result 2026-11-15 (20 messages): before the DETECT change 8/9 caught, 0/9 false; after it 9/9 caught, 0/11 false (11 = 9 + the 2 constructed negatives).
result 2026-11-16 (26 messages, 6 negatives added from the misfires; 3 runs): first DETECT 8-9/9 caught, 2/17 false ('keep it in the idea',
'keep, and yes'); with the "First: ... ANSWERS that question" rule 8/9 caught in all 3 runs (one miss per run, not always the same), 0/17 false.
Usage: python -I scripts/recall/eval_decisions.py   (calls the real cheap model once per message; exit 1 on a false draft)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain, decisions

# (previous assistant turn, his real message, is it a design decision? (labelled by hand))
SET = [
    ("I built a map as an artifact; it is hosted on claude.ai.", "dont like artifacts i want the same thing with an html file", True),
    ("A plain explanation of how the hooks work.", "actually i dont understand the map so much can you just tell me simply how it works in steps", False),
    ("Proposed: rebuild the map; top level 3-7 boxes.", "the whole idea of nesting is that the top level is simple and answers my questions and going deeper explains in more detail and how it works", True),
    ("Asked: regroup the 16 top boxes into 3-7?", "its not a fixed number of boxes as much as it needs to show me the steps in the pipeline", True),
    ("Showed the 13-step top level.", "the more nested the less top and more specific thats the idea", True),
    ("Showed the regrouped map.", "that is much nicer well done", False),
    ("Said the gate blocked; asked about the setup.", "did you read all the setup i dont wanna talk to you for nothing", False),
    ("Proposed option A or B for who starts agents.", "a. is the updating a map design working or is it gonna make it from scratch like youve done so far?", True),
    ("Listed the implementer chain.", "i meant the reviewer how that works isnt there a loop? i remember there was something", False),
    ("Explained the loop is only a CLAUDE.md rule.", "the setup_manager can also decide that from hooks and not from memory", True),
    ("Listed the 4 fixes and asked to push.", "yes and yes and why does updating take so long its not building everything?", False),
    ("Proposed the SDD tree design with 4 refinements.", "where you said code changes the sdd first. no we write code check stuff until i like it and approve and only then sdd", True),
    ("Asked: why required at every level?", "instead of summary call it feature instead of why say value", True),
    ("Asked: build validator, generator, convert, trial?", "yes", True),
    ("Reported a reviewer's 9 findings and asked to fix all.", "ok", False),
    ("Showed the setup map.", "by the way does the setup have a diary? ideas? weve done quite a lot", False),
    ("Explained the map uses wrong order and jargon.", "i clicked by mistake i dont know what even was that", False),
    ("Listed what is saved in the lesson.", "dont tell me what you did and what you enriched tell me what you saved", False),
    # constructed (not real messages): the two exclusions added to DETECT on 2026-11-15
    ("Showed the settings card.", "make the button blue", False),
    ("Found a null check missing in the parser and proposed adding it.", "yes fix it", False),
    # misfires of 2026-11-16: answers about a diary draft, an idea to park, a one-time choice (the first four are his words as
    # quoted in tasks/todo.md; the park idea and the one-time choice are constructed)
    ("Diary (DESIGN_DECISIONS_DIARY.md): Keep the map simple - 'the map is simple'. Add it?", "discard", False),
    ("Diary (DESIGN_DECISIONS_DIARY.md): Map follows the SDD - 'regenerate it'. Add it?", "keep it in the idea", False),
    ("Diary (DESIGN_DECISIONS_DIARY.md): Gate waits for review - 'wait for the review'. Add it?", "yes add it", False),
    ("Diary (DESIGN_DECISIONS_DIARY.md): Capture skips discards - 'skip them'. Add it?", "keep, and yes", False),
    ("Listed the gate fixes.", "maybe later we could add a second model that reviews the gate's verdicts", False),
    ("Asked: which of the two files to open first?", "use the first one for now", False),
]

tp = fp = fn = tn = tok = 0
for prev, msg, want in SET:
    out, t = brain.ask(decisions.DETECT.format(prev=prev, prompt=msg), tag="eval-decision")
    tok += t
    got = out.strip().upper().startswith("YES")
    tp += got and want; fp += got and not want; fn += want and not got; tn += not got and not want
    print(f"{'OK ' if got == want else 'BAD'} want={want!s:5} got={got!s:5} | {msg[:70]}")
print(f"\ndecisions caught {tp}/{tp+fn}, false drafts {fp}/{fp+tn}, tokens {tok}")
sys.exit(1 if fp else 0)
