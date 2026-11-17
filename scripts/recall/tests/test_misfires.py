"""The gate and delegation misfires of 2026-11-16: a change waiting for its review, a background agent's result, the input step on
diary answers and the SDD question, the one test command satisfying the TESTER rule."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, ctx, decisions, delegate, delegvet, diary, flags, gate, grounding, pending, turnfacts
from test_delegate import step, ROOT
from test_diary import Env, DIARY, DRAFT


class WaitingForReview(unittest.TestCase):
    def test_a_change_announced_for_review_is_blocked_again_the_wide_veto_was_removed(self):
        root = h.git_repo({"scripts/a.py": "1"})
        f = os.path.join(root, "scripts", "a.py")
        open(f, "w").write("2")
        tp = h.transcript([h.user("go"), h.assistant(h.tool("Edit", {"file_path": f, "old_string": "1", "new_string": "2"})),
                           h.assistant("Built it. Next the reviewer checks it, then the commit.")])
        with mock.patch.object(delegate.turnfacts.setupstate, "git_changed", return_value=["scripts/a.py"]):
            brain.ask = h.brain_says("BLOCK SETUP-MANAGER | scripts/a.py is not committed")
            self.assertEqual(delegate.output_step(tp, root)[0][0], "SETUP-MANAGER")  # no longer vetoed by the words "reviewer next"

    def test_a_reviewer_still_running_holds_the_commit_back(self):
        root = h.git_repo({"scripts/a.py": "1"})
        es = [h.user("go"), *h.launch("reviewer", "rv", "t5"), h.assistant("Waiting for the reviewer.")]
        with mock.patch.object(delegate.turnfacts.setupstate, "git_changed", return_value=["scripts/a.py"]):
            brain.ask = h.brain_says("BLOCK SETUP-MANAGER | not committed")
            self.assertIsNone(delegate.output_step(h.transcript(es), root)[0])


class AgentResultDuringTheTurn(unittest.TestCase):
    def test_a_result_that_arrives_counts_as_that_agents_work(self):
        started = [h.user("make it"), *h.launch("tester", "ag2", "t2"), h.assistant("Started the tester.")]
        arrived = [h.user("and?"), h.assistant(h.tool("Edit", {"file_path": os.path.join(ROOT, "scripts", "recall", "x.py"), "old_string": "a", "new_string": "b"})),
                   h.notice("ag2", "t2", "TEST RESULT: 31 passed"), h.assistant("The tester says all pass.")]
        t = turnfacts.turn(h.transcript(started + arrived), ROOT)
        self.assertIn("tester", t["called"])
        self.assertTrue(any("31 passed" in x for x in t["tools"]), "the brain must see what the agent returned")
        self.assertIsNone(step(started + arrived, "BLOCK TESTER | no test ran")[0])  # the tester's work arrived this turn


class InputStep(unittest.TestCase):
    def say(self, prev, prompt, reply):
        brain.ask = h.brain_says(reply)
        return delegate.input_step(prompt, h.transcript([h.user("x"), h.assistant(prev), h.user(prompt)]))[0]

    def test_a_diary_answer_is_never_the_implementer(self):
        asked = "Diary (D.md): Keep the map simple - 'the map is simple'. Add it?"
        for answer in ("yes add it", "keep, and yes"):
            self.assertEqual(self.say(asked, answer, "IMPLEMENTER | he approves"), [], answer)
        self.assertEqual(len(self.say("Proposed option A.", "yes do it", "IMPLEMENTER | he approves")), 1)  # control

    def test_sdd_question_is_built_from_the_brain_and_asked_once(self):
        got = self.say("The retry works.", "good, nice", "SDD-ASK | payment retry | a failed payment is retried once")
        self.assertEqual(len(got), 1)
        self.assertIn('"SDD: update the SDD for payment retry? (it changed: a failed payment is retried once)"', got[0])
        asked = "SDD: update the SDD for payment retry? (it changed: x)"
        self.assertEqual(self.say(asked, "also nice", "SDD-ASK | payment retry | x"), [], "never asked twice")
        km = self.say(asked, "yes", "KNOWLEDGE-MANAGER | he said yes to the SDD update")
        self.assertIn("knowledge-manager", km[0])

    def test_the_draft_and_the_code_know_the_new_kind(self):
        self.assertEqual(delegate.check_sources(), [])
        self.assertIn("SDD-ASK", delegate.INPUT_KINDS)
        self.assertIn("SDD-ASK", delegate._lines("Instruction lines attached"))


class TesterRule(unittest.TestCase):
    def test_running_the_one_test_command_satisfies_the_tester_rule(self):
        edit = h.assistant(h.tool("Edit", {"file_path": os.path.join(ROOT, "scripts", "recall", "x.py"), "old_string": "a", "new_string": "b"}), "Changed it.")
        run = h.assistant(h.tool("Bash", {"command": "python -I scripts/run_chosen_checks.py"}), "Ran everything; PASSED.")
        self.assertEqual(step([h.user("x"), edit, run], "BLOCK TESTER | no test ran")[0][0], "TESTER-HERE")  # a test ran, but in the main session
        self.assertEqual(step([h.user("x"), edit], "BLOCK TESTER | no test ran")[0][0], "TESTER")  # control: nothing ran
        self.assertNotIn("ran_all", turnfacts.turn(h.transcript([h.user("x"), edit, run]), ROOT))  # no veto of its own: only the tester agent satisfies the rule

    def test_the_block_reason_says_call_the_tester_agent(self):
        got = step([h.user("x"), h.assistant(h.tool("Edit", {"file_path": os.path.join(ROOT, "scripts", "recall", "x.py"), "old_string": "a", "new_string": "b"}), "Changed it.")], "BLOCK TESTER | no test ran")[0]
        self.assertIn("call the tester agent", got[1])


class TesterHere(unittest.TestCase):
    bash = lambda self, c: h.assistant(h.tool("Bash", {"command": c}), "Ran it.")

    def test_a_suite_run_in_the_main_session_is_blocked(self):
        got = step([h.user("x"), self.bash("python -I scripts/recall/tests/run_tests.py")], "OK")
        self.assertEqual(got[0][0], "TESTER-HERE")
        self.assertIn("call the tester agent", got[0][1])
        self.assertEqual(got[1].prompts, [], "decided by the code: no brain call")

    def test_the_tester_agent_or_small_reads_do_not_block(self):
        called = [h.user("x"), self.bash("python -I scripts/recall/tests/run_tests.py"), *h.launch("tester", "tg", "t3")]
        self.assertIsNone(step(called, "OK")[0])  # the tester agent was called AFTER the run: excused
        before = [h.user("x"), *h.launch("tester", "tg", "t3"), self.bash("python -I scripts/recall/tests/run_tests.py")]
        self.assertEqual(step(before, "OK")[0][0], "TESTER-HERE")  # a tester call BEFORE the run does not excuse it
        for c in ("python -I scripts/recall/gate_report.py --out test.json", "python x.py  # then run_tests.py", "python -c 'import test_a'", "git commit -m 'run_tests.py'"):
            self.assertIsNone(step([h.user("x"), self.bash(c)], "OK")[0], c)  # names inside a comment, a .json or a message are no suite
        for c in ("git log --oneline", "git status", "ls scripts", "grep -n run_tests.py scripts/x.py", "cat scripts/recall/tests/run_tests.py"):
            self.assertIsNone(step([h.user("x"), self.bash(c)], "OK")[0], c)
        for c in ("node skills/sdd/scripts/test-sdd.js", "python -I scripts/run_chosen_checks.py", "pytest -q", "npm test", "python -I scripts/recall/eval_decisions.py",
                  "python -I scripts/recall/capture.py check"):
            self.assertEqual(step([h.user("x"), self.bash(c)], "OK")[0][0], "TESTER-HERE", c)


if __name__ == "__main__":
    unittest.main()
