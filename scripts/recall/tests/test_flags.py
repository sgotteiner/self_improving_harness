"""Flags capture on a scratch copy of the flags file (never the real one): 3 items -> 3 lines, no section -> nothing, the
same choices again -> deduped, what he asked only from his words, the scrub, the lost-update race, the per-message cap.
Uses the real local embedder (no brain call, no network)."""
import datetime, os, tempfile, unittest

import helpers as h
import ctx, diary, flags

FLAGS = ("---\ntags: [x]\n---\n\n# Flags\n\n## Claude-on-its-own (2026-10-24)\n- **Usage line through settings** — owner asked: every session\n\n"
         "## Known debt (2026-11-15)\n- something deferred\n")
REPORT = "Done.\n\n## Choices beyond the spec\n- used a lockfile\n- named the folder drafts\n- kept the old endpoint\n"
REPLY = ("a lockfile to stop two writers | writes to never collide with each other\n"
         "a folder named drafts for pending files | (not stated)\n"
         "kept the old endpoint alongside the new one | the owner asked to add a new one\n")
HUMAN = "I want writes to never collide with each other"


class Flags(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.path = os.path.join(d, "DIARY_FLAGS.md")
        open(self.path, "w", encoding="utf-8", newline="").write(FLAGS)
        diary.DIARY_SETUP, diary.FLAGS_SETUP = os.path.join(d, "DIARY.md"), self.path
        flags.VAULT = d  # the scratch folder stands for the private vault
        open(diary.DIARY_SETUP, "w").write("# d")

    def session(self, *reports):
        es = [h.user(HUMAN)]
        for r in reports:
            t = h.tool("Agent", {"subagent_type": "implementer", "description": "d"})
            es += [h.assistant(t), h.result(t["id"], r)]
        return h.transcript(es + [h.assistant("ok")], cwd=ctx.ROOT)

    def ask(self, reply):
        a = h.brain_says(reply)
        return a, lambda p, system="", tag="": a(p)

    def text(self):
        return open(self.path, encoding="utf-8").read()

    def test_three_choices_become_three_lines_under_a_dated_section(self):
        a, ask = self.ask(REPLY)
        self.assertEqual(len(flags.process(self.session(REPORT), ask)), 3)
        t = self.text()
        head = flags.HEADING.format(date=datetime.date.today())
        self.assertTrue(t.index("2026-10-24") < t.index(head) < t.index("## Known debt"), t)
        self.assertEqual(t[t.index(head):t.index("## Known debt")].count("\n- "), 3)
        self.assertTrue(t.startswith(FLAGS.split("## Known debt")[0].rstrip()))

    def test_what_he_asked_is_his_words_or_not_stated(self):
        flags.process(self.session(REPORT), self.ask(REPLY)[1])
        t = self.text()
        self.assertIn('**a lockfile to stop two writers** — owner asked: "writes to never collide with each other"', t)
        self.assertIn("**kept the old endpoint alongside the new one** — owner asked: (not stated)", t)  # the brain's guess is never written
        self.assertNotIn("add a new one", t)

    def test_a_return_without_choices_changes_nothing_and_costs_no_call(self):
        a, ask = self.ask(REPLY)
        self.assertEqual(flags.process(self.session("All done. Tests pass."), ask), [])
        self.assertEqual((a.prompts, self.text()), ([], FLAGS))

    def test_the_same_choices_again_are_deduped(self):
        a, ask = self.ask(REPLY)
        flags.process(self.session(REPORT), ask)
        once = self.text()
        self.assertEqual(flags.process(self.session(REPORT), ask), [])
        self.assertEqual(self.text(), once)

    def test_a_return_is_read_once_per_session(self):
        a, ask = self.ask(REPLY)
        tp = self.session(REPORT)
        flags.process(tp, ask), flags.process(tp, ask)
        self.assertEqual(len(a.prompts), 1)

    def test_no_flags_file_means_nothing_is_written(self):
        os.remove(self.path)
        self.assertEqual(flags.process(self.session(REPORT), self.ask(REPLY)[1]), [])
        self.assertFalse(os.path.exists(self.path))

    def test_an_edit_made_during_the_brain_call_is_not_lost(self):
        def ask(p, system="", tag=""):
            open(self.path, "a", encoding="utf-8", newline="").write("- added by someone else meanwhile\n")
            return REPLY, 1
        flags.process(self.session(REPORT), ask)
        self.assertIn("added by someone else meanwhile", self.text())
        self.assertIn("a lockfile to stop two writers", self.text())

    def test_scrub_applies_outside_the_vault_only(self):
        reply = "wrote the report to mail me@example.com | (not stated)\n"
        flags.VAULT = os.path.join(tempfile.mkdtemp(), "elsewhere")  # now the file is not in the vault: it may be public
        self.assertEqual(flags.process(self.session(REPORT), self.ask(reply)[1]), [])
        flags.VAULT = os.path.dirname(self.path)
        self.assertEqual(len(flags.process(self.session(REPORT), self.ask(reply)[1])), 1)  # a new session, private file: kept

    def test_cap_per_message_and_one_failing_return_does_not_stop_the_rest(self):
        calls = []
        def ask(p, system="", tag=""):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("model failed")
            return REPLY, 1
        reports = [REPORT + f" run {i}" for i in range(3)]
        flags.MAX_RETURNS = 2
        try:
            new = flags.process(self.session(*reports), ask)
        finally:
            flags.MAX_RETURNS = 10
        self.assertEqual(len(calls), 2)  # the cap, counted per message
        self.assertEqual(len(new), 3)  # the first return failed, the second still gave its items


if __name__ == "__main__":
    unittest.main()
