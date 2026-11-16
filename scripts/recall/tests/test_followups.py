"""Reviewer follow-ups: filler spans, flags state and caps, editing a draft on approval, the draft note, the gate's timeout."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import ctx, decisions, diary, flags, gate, grounding
from test_diary import Env, DIARY


class Grounding(unittest.TestCase):
    def test_a_span_of_filler_words_grounds_nothing(self):
        self.assertEqual(grounding.common_span("he wants it to work and that", "i want it to work and that now ok"), "")
        self.assertEqual(grounding.common_span("because the map is simple and clear", "the map is simple and clear"), "the map is simple and clear")


class FlagsState(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.path = os.path.join(d, "DIARY_FLAGS.md")
        open(self.path, "w", encoding="utf-8").write("# Flags\n\n## Known debt (2026-11-15)\n- x\n")
        diary.DIARY_SETUP, diary.FLAGS_SETUP, flags.VAULT, flags.STATE = os.path.join(d, "D.md"), self.path, d, os.path.join(d, "st")
        open(diary.DIARY_SETUP, "w").write("# d")
        t = h.tool("Agent", {"subagent_type": "implementer", "description": "d"})
        self.tp = h.transcript([h.user("x"), h.assistant(t), h.result(t["id"], "## Choices beyond the spec\n- a")], cwd=ctx.ROOT)

    def test_a_failed_write_leaves_the_return_unread(self):
        ask = lambda p, system="", tag="": ("a lockfile for writers | (not stated)", 1)
        with mock.patch.object(flags.mdfile, "write_atomic", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                flags.process(self.tp, ask)
        self.assertFalse(os.path.exists(flags._state(self.tp)), "state must not be saved before the write succeeded")
        self.assertEqual(len(flags.process(self.tp, ask)), 1)  # the next message retries it and succeeds

    def test_items_per_return_and_their_length_are_capped(self):
        reply = "\n".join(f"choice number {i} {'x' * 500} | (not stated)" for i in range(30))
        items = flags.items_of(reply, [])
        self.assertEqual(len(items), flags.MAX_ITEMS)
        self.assertTrue(all(len(i) < flags.MAX_ITEM_LEN + 80 for i in items))


class Drafts(Env):
    def test_approve_with_a_corrected_title_and_idea(self):
        open(self.diary, "w", encoding="utf-8").write(DIARY)
        self.draft()
        self.assertEqual(decisions._cli(["decisions.py", "approve", "new-one", "--title", "Fixed title", "--idea", "the fixed idea"]), 0)
        t = open(self.diary, encoding="utf-8").read()
        self.assertIn("### Fixed title", t)
        self.assertIn("**Idea:** the fixed idea", t)
        self.assertNotIn("### New one", t)

    def test_plain_approve_still_uses_the_draft(self):
        open(self.diary, "w", encoding="utf-8").write(DIARY)
        self.draft()
        self.assertEqual(decisions._cli(["decisions.py", "approve", "new-one"]), 0)
        self.assertIn("### New one", open(self.diary, encoding="utf-8").read())

    def test_the_note_names_the_target_diary_and_the_edit_option(self):
        self.draft()
        (path, note), = decisions.ask_notes()
        self.assertIn("Diary (diary.md)", note)
        self.assertIn("--title", note)
        text = open(path, encoding="utf-8").read().replace(self.diary.replace("\\", "/"), "")
        open(path, "w", encoding="utf-8").write(text)
        self.assertIn("no diary found", decisions.ask_notes()[0][1])
        self.assertIn("Add it?", note)  # the answer to it is recognised as a diary answer by process() and the input step


class GateTimeout(unittest.TestCase):
    def test_the_limit_is_read_from_settings_json(self):
        s = json.load(open(os.path.join(ctx.ROOT, "settings.json"), encoding="utf-8"))
        want = next(x["timeout"] for g in s["hooks"]["Stop"] for x in g["hooks"] if "gate.py" in x["command"])
        self.assertEqual(gate.STOP_LIMIT, want)
        d = tempfile.mkdtemp()
        open(os.path.join(d, "settings.json"), "w").write(json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "python gate.py", "timeout": 77}]}]}}))
        with mock.patch.object(ctx, "ROOT", d):
            self.assertEqual(gate.stop_limit(), 77)
            open(os.path.join(d, "settings.json"), "w").write("{}")
            self.assertEqual(gate.stop_limit(), 180)


if __name__ == "__main__":
    unittest.main()
