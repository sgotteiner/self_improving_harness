"""Output step, input step and turn facts: resumed agents, setup-edit detection, hedges, background agents, the skip."""
import os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, ctx, delegate, setupstate, turnfacts

ROOT = ctx.ROOT


def step(entries, reply, root=ROOT):
    brain.ask = h.brain_says(reply)
    tp = h.transcript(entries)
    return delegate.output_step(tp, root)[0], brain.ask


EDIT = lambda f="scripts/recall/x.py": h.assistant(h.tool("Edit", {"file_path": f, "old_string": "a", "new_string": "b"}), "Changed it.")


class Resumed(unittest.TestCase):
    def test_every_rule_counts_a_resumed_agent(self):
        for kind, block in (("reviewer", "REVIEWER"), ("tester", "TESTER"), ("knowledge-manager", "KNOWLEDGE-MANAGER"),
                            ("setup-manager", "SETUP-MANAGER")):
            earlier = [h.user("start"), *h.launch(kind, "ag1", "t1"), h.notice("ag1", "t1")]
            now = [h.user("go on"), EDIT(), *h.resume("ag1"), h.notice("ag1", "t1")]
            with self.subTest(kind=kind):
                self.assertIsNone(step(earlier + now, f"BLOCK {block} | missing")[0], "a resumed agent must count as called")
                got = step(earlier + now[:2], f"BLOCK {block} | missing")[0]  # control: the same turn without the resume
                self.assertEqual(got[0] if got else None, block)

    def test_resumed_implementer_is_an_implementer_call(self):
        es = [h.user("start"), *h.launch("implementer", "ag1", "t1"), h.notice("ag1", "t1"), h.user("again"), *h.resume("ag1")]
        t = turnfacts.turn(h.transcript(es), ROOT)
        self.assertIn("implementer", t["called"])
        self.assertIn("IMPLEMENTER", t["facts"])

    def test_agent_type_matched_by_substring(self):
        es = [h.user("x"), h.assistant(h.tool("Agent", {"subagent_type": "my-reviewer-v2", "description": "d"})), h.assistant("ok")]
        self.assertEqual(turnfacts.turn(h.transcript(es), ROOT)["called"], ["reviewer"])


class SetupEdits(unittest.TestCase):
    def setUp(self):
        self.root = h.git_repo({"scripts/a.py": "1", "tasks/delegation-draft.md": "d", "tasks/todo.md": "t", "scripts/b.py": "1"})
        self.tp = h.transcript([h.user("change it"), h.assistant("done")])
        open(os.path.join(self.root, "scripts", "b.py"), "w").write("2")  # dirty before his message
        setupstate.save_snapshot(self.tp, self.root)

    def test_git_diff_against_the_turn_start(self):
        for rel, text in (("scripts/a.py", "22"), ("tasks/delegation-draft.md", "dd"), ("tasks/todo.md", "tt")):
            open(os.path.join(self.root, rel), "w").write(text)
        os.makedirs(os.path.join(self.root, "scripts/recall/results"))
        open(os.path.join(self.root, "scripts/recall/results/run.json"), "w").write("{}")  # generated
        self.assertEqual(sorted(turnfacts.turn(self.tp, self.root)["setup"]), ["scripts/a.py", "tasks/delegation-draft.md"])

    def test_nothing_changed_since_the_snapshot(self):
        self.assertEqual(turnfacts.turn(self.tp, self.root)["setup"], [])

    def test_a_failed_snapshot_deletes_the_stale_one(self):
        open(os.path.join(self.root, "scripts/a.py"), "w").write("44")
        self.assertEqual(turnfacts.turn(self.tp, self.root)["setup"], ["scripts/a.py"])  # the snapshot of setUp is in use
        with mock.patch.object(setupstate, "git_state", return_value=None):
            with self.assertRaises(OSError):
                setupstate.save_snapshot(self.tp, self.root)
        self.assertEqual(turnfacts.turn(self.tp, self.root)["setup"], [], "the old snapshot must not be used for the new turn")

    def test_setup_manager_must_come_after_the_edit(self):
        open(os.path.join(self.root, "scripts/a.py"), "w").write("33")
        f = os.path.join(self.root, "scripts", "a.py")
        before = [h.user("change it"), *h.launch("setup-manager", "sm", "t9"), EDIT(f)]
        after = [h.user("change it"), EDIT(f), *h.launch("setup-manager", "sm", "t9")]
        self.assertFalse(turnfacts.turn(h.transcript(before), self.root)["sm_ok"])
        self.assertTrue(turnfacts.turn(h.transcript(after), self.root)["sm_ok"])
        self.assertIsNone(step(after, "BLOCK SETUP-MANAGER | not committed", self.root)[0])


class Verdicts(unittest.TestCase):
    def test_a_reason_that_leads_with_a_hedge_does_not_block_but_a_hedge_inside_a_finding_does(self):
        es = [h.user("x"), EDIT()]
        self.assertIsNone(step(es, "BLOCK TESTER | this may be OK, nothing to test")[0])
        self.assertIsNone(step(es, "BLOCK TESTER | Unclear whether it matters")[0])
        got = step(es, "BLOCK TESTER | Tests were not run; unclear which file changed, run the tester")[0]
        self.assertEqual(got[0], "TESTER")  # a real finding with a hedge later in it still blocks
        self.assertEqual(step(es, "BLOCK TESTER | no test ran")[0][0], "TESTER")

    def test_nothing_edited_called_or_claimed_skips_the_brain(self):
        got, ask = step([h.user("what is a hook?"), h.assistant("A hook is a script the harness runs.")], "BLOCK TESTER | x")
        self.assertIsNone(got)
        self.assertEqual(ask.prompts, [])

    def test_background_agent_still_running(self):
        started = [h.user("make it"), *h.launch("implementer", "ag1", "t1"), h.assistant("Started the implementer; I'll report when it returns.")]
        self.assertIsNone(step(started, "BLOCK TESTER | call the tester")[0])
        self.assertIsNone(step(started, "BLOCK REVIEWER | review it")[0])
        claimed = started[:-1] + [h.assistant("The change is fixed and ready.")]  # the final message itself claims it is done
        self.assertEqual(step(claimed, "BLOCK TESTER | no test ran")[0][0], "TESTER")
        returned = started[:3] + [h.notice("ag1", "t1"), h.assistant("The implementer returned; changed the code.")]
        self.assertEqual(step(returned, "BLOCK TESTER | call the tester")[0][0], "TESTER")  # it returned: the rule applies again
        self.assertEqual(turnfacts.turn(h.transcript(started), ROOT)["pending"], ["implementer"])

    def test_the_round_limit_is_a_constant_in_the_prompt(self):
        _, ask = step([h.user("x"), EDIT()], "OK")
        self.assertIn(f"at most {turnfacts.ROUNDS_MAX} rounds", ask.prompts[0])


class InputAndSources(unittest.TestCase):
    def test_a_question_is_never_knowledge_manager(self):
        brain.ask = h.brain_says("NONE")
        self.assertEqual(delegate.input_step("is the sdd also updated?", "")[0], [])
        brain.ask = h.brain_says("KNOWLEDGE-MANAGER | he says it is done")
        self.assertEqual(len(delegate.input_step("done, looks right. is the retry path also covered?", "")[0]), 1)  # done AND a question
        self.assertNotIn('"?" in prompt', open(delegate.__file__, encoding="utf-8").read())  # no code filter on question marks
        self.assertIn("also asks something still counts", open(delegate.DRAFT, encoding="utf-8").read())  # the draft says it

    def test_capture_check_fails_on_a_bad_source(self):
        import casesave, index
        with mock.patch.object(delegate, "check_sources", return_value=["boom"]), mock.patch.object(index, "case_files", return_value=[]):
            self.assertFalse(casesave.check_all())

    def test_renamed_headings_fail_loudly(self):
        self.assertEqual(delegate.check_sources(), [])
        d = tempfile.mkdtemp()
        a, b = os.path.join(d, "CLAUDE.md"), os.path.join(d, "draft.md")
        open(a, "w").write("## Core rules\nx\n## Next\n")
        open(b, "w").write(open(delegate.DRAFT, encoding="utf-8").read().replace("## Output step", "## Output stage"))
        old = delegate.CLAUDE_MD, delegate.DRAFT
        delegate.CLAUDE_MD, delegate.DRAFT = a, b
        try:
            bad = delegate.check_sources()
        finally:
            delegate.CLAUDE_MD, delegate.DRAFT = old
        self.assertTrue(any("The core" in p for p in bad) and any("Output step" in p for p in bad), bad)


if __name__ == "__main__":
    unittest.main()
