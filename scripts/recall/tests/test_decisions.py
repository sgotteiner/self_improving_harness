"""Decision capture: the detector side (the why check, the target diary, one call on a first message)."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, ctx, decisions, diary
from test_diary import Env


class Process(Env):
    def run_process(self, replies, prompt, entries):
        seq = iter(replies)
        calls = []
        def ask(p, system="", tag=""):
            calls.append(tag)
            return next(seq), 1
        brain.ask = ask
        with mock.patch.object(diary, "duplicate", return_value=None):
            return decisions.process(prompt, h.transcript(entries)), calls

    def test_a_why_he_did_not_say_is_not_kept(self):
        self.assertTrue(decisions.grounded("because the map is simple", "the map is simple and clear"))
        self.assertFalse(decisions.grounded("it keeps the setup stable", "yes do it"))
        self.assertFalse(decisions.grounded("he said yes because it saves money", "yes"))  # under 3 words: grounds nothing
        self.assertFalse(decisions.grounded("because it is simple", "yes it is simple"))  # 3 shared words are under the 4-word minimum
        reply = json.dumps({"title": "T", "idea": "I", "why": "it keeps the setup stable"})
        (path, _), calls = self.run_process(["YES | d", reply], "a. go with option a", [h.user("x"), h.assistant("A or B?")])
        self.assertIn('why: "(not stated)"', open(path, encoding="utf-8").read())
        reply = json.dumps({"title": "T2", "idea": "I", "why": "he said: option a is simpler"})
        (path, _), _ = self.run_process(["YES | d", reply], "option a is simpler than b", [h.user("x"), h.assistant("A or B?")])
        self.assertIn("option a is simpler", open(path, encoding="utf-8").read().split("why:")[1])

    def test_a_decision_about_the_setup_goes_to_the_setup_diary_from_any_folder(self):
        setup = os.path.join(self.d, "SETUP_DIARY.md")
        open(setup, "w").write("# d")
        other = os.path.join(self.d, "proj")
        os.makedirs(other)  # a work project without any diary
        reply = lambda about: json.dumps({"title": "T" + about, "idea": "I", "why": "(not stated)", "about": about})
        with mock.patch.object(diary, "DIARY_SETUP", setup):
            es = [h.user("x"), h.assistant("A or B for the hooks?")]
            (path, _), _ = self.run_process(["YES | d", reply("setup")], "a. go with option a", es)
            self.assertIn(setup.replace("\\", "/"), open(path, encoding="utf-8").read().replace("\\", "/"))
            (path, _), _ = self.run_process(["YES | d", reply("project")], "a. go with option a", es)  # not about the setup, session elsewhere
            self.assertIn('target: ""', open(path, encoding="utf-8").read())  # no diary found: he is asked
            edit = h.assistant(h.tool("Edit", {"file_path": os.path.join(ctx.ROOT, "scripts", "recall", "x.py"), "old_string": "a", "new_string": "b"}))
            (path, _), _ = self.run_process(["YES | d", reply("project2")], "a. go with option a", [h.user("x"), edit, h.assistant("changed")])
            self.assertIn("SETUP_DIARY", open(path, encoding="utf-8").read())  # the turn edited setup files

    def test_inferred_whys_in_a_diary_fail_the_check(self):
        import casesave
        root = tempfile.mkdtemp()
        for name, text in (("clean", "**Why:** (not stated)"), ("dirty", "**Why:** (inferred) guessed")):
            os.makedirs(os.path.join(root, name, "docs"))
            open(os.path.join(root, name, "docs", "D.md"), "w").write(text)
            open(os.path.join(root, name, "CLAUDE.md"), "w").write("## Project documents\n- **Diary:** `docs/D.md`\n")
        with mock.patch.object(diary, "DIARY_SETUP", os.path.join(root, "none.md")):
            self.assertEqual(casesave.inferred_in(root), [os.path.join(root, "dirty", "docs", "D.md")])

    def test_first_message_is_still_detected_with_one_call(self):
        (path, _), calls = self.run_process(["NO"], "from now on every table has an owner", [])
        self.assertEqual(calls, ["decision-detect"])

    def test_previous_turn_is_not_truncated(self):
        long = "start " + "word " * 1000 + "THE-END"
        seen = []
        brain.ask = lambda p, system="", tag="": (seen.append(p), ("NO", 1))[1]
        decisions.process("ok", h.transcript([h.user("x"), h.assistant(long), h.user("ok")]))
        self.assertIn("THE-END", seen[0])


if __name__ == "__main__":
    unittest.main()
