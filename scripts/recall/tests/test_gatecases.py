"""The gate learning from its false alarms: LOOP only on a failure, SETUP-MANAGER not while a review asked for fixes, the label
when the session says a block was a false alarm, the regression case that results, and eval_gate.py replaying it."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import brain, delegate, delegvet, eval_gate, gatecases, turnfacts, verdicts
from test_delegate import step, ROOT


def lines(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


class Loop(unittest.TestCase):
    def turn(self, result):
        return [h.user("x"), *h.launch("implementer", "i1", "t1"), h.notice("i1", "t1"), *h.launch("tester", "t2", "t2x"), h.notice("t2", "t2x", result),
                h.assistant("The tester ran.")]

    def test_loop_needs_a_result_that_says_the_purpose_fell_short(self):
        self.assertIsNone(step(self.turn("71 tests, all passed"), "BLOCK LOOP | start round 2")[0])
        self.assertEqual(step(self.turn("FAILED (failures=3): the purpose fell short"), "BLOCK LOOP | start round 2")[0][0], "LOOP")
        self.assertTrue(turnfacts.turn(h.transcript(self.turn("Traceback (most recent call last)")), ROOT)["fell_short"])


class ReviewAskedForFixes(unittest.TestCase):
    def run_step(self, entries):
        with mock.patch.object(delegate.turnfacts.setupstate, "git_changed", return_value=["scripts/a.py"]):
            brain.ask = h.brain_says("BLOCK SETUP-MANAGER | scripts/a.py is not committed")
            return delegate.output_step(h.transcript(entries), ROOT)[0]

    def test_no_commit_while_the_latest_review_asked_for_fixes_that_are_not_done(self):
        review = [h.user("go"), *h.launch("reviewer", "rv", "t4"), h.notice("rv", "t4", "Fix first: the state is saved before the write. Blocking.")]
        self.assertIsNone(self.run_step(review + [h.assistant("The reviewer wants one fix first.")]))
        fixed = review + [h.assistant(h.tool("Edit", {"file_path": os.path.join(ROOT, "scripts", "a.py"), "old_string": "a", "new_string": "b"}), "Fixed it.")]
        self.assertEqual(self.run_step(fixed)[0], "SETUP-MANAGER")  # the fix came after the review: the commit is due
        clean = [h.user("go"), *h.launch("reviewer", "rv", "t4"), h.notice("rv", "t4", "Looks good, no findings."), h.assistant("Reviewed.")]
        self.assertEqual(self.run_step(clean)[0], "SETUP-MANAGER")


class Labelling(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self._old = os.environ.get("RECALL_VERDICT_LOG"), gatecases.SET
        os.environ["RECALL_VERDICT_LOG"] = os.path.join(d, "v.jsonl")
        gatecases.SET = os.path.join(d, "set.jsonl")

    def tearDown(self):
        os.environ["RECALL_VERDICT_LOG"], gatecases.SET = self._old

    def blocked_turn(self):
        """A transcript where the gate blocked the first reply (REVIEWER while the implementer was building), logged for real."""
        es = [h.user("build it"), *h.launch("implementer", "i1", "t1"), h.assistant("The implementer is still building.")]
        tp = h.transcript(es)
        brain.ask = h.brain_says("BLOCK REVIEWER | call the reviewer")
        with mock.patch.object(delegate, "veto", return_value=None):  # as if the veto had not existed: the block is sent
            self.assertEqual(delegate.output_step(tp, ROOT)[0][0], "REVIEWER")
        verdicts.log(tp, "gate", "SENT")
        return tp, es

    def test_a_reply_that_calls_the_block_a_false_alarm_labels_it_and_makes_a_case(self):
        tp, es = self.blocked_turn()
        with open(tp, "a", encoding="utf-8") as f:
            f.write(json.dumps(h.assistant("That block was a false alarm: the implementer is still building.")) + "\n")
        self.assertEqual(gatecases.label(tp), ["delegation:REVIEWER"])
        got = lines(os.environ["RECALL_VERDICT_LOG"])
        self.assertEqual([r["verdict"] for r in got if r["src"] == "label"], ["FALSE_ALARM"])
        (case,) = lines(gatecases.SET)
        self.assertEqual((case["rule"], case["expect"], case["features"]["pending"]), ("REVIEWER", "no_block", ["implementer"]))
        text = open(gatecases.SET, encoding="utf-8").read()
        for word in ("building", "build it", "implementer is"):
            self.assertNotIn(word, text, "no words of the turn in the tracked case file")
        self.assertIsNone(gatecases.label(tp))  # once only
        self.assertEqual(len(lines(gatecases.SET)), 1)

    def test_the_reply_names_the_rule_it_calls_a_false_alarm(self):
        feat = dict(called=[], pending=[], claims=False, sm_ok=True, fell_short=False, review_open=False,
                    suite_unexcused=False, edited=True, returned=False)
        tp = h.transcript([h.user("x"), h.assistant("a")])
        add = lambda *es: open(tp, "a", encoding="utf-8").writelines(json.dumps(e) + "\n" for e in es)
        verdicts.log(tp, "delegation", "BLOCK", "LOOP", features=feat)
        verdicts.log(tp, "gate", "SENT")
        add(h.assistant("b"), h.assistant("c"))
        verdicts.log(tp, "delegation", "BLOCK", "TESTER-HERE", features=dict(feat, suite_unexcused=True))
        verdicts.log(tp, "gate", "SENT")
        add(h.assistant("That is a false alarm from the loop rule. Nothing fell short."))
        self.assertEqual(gatecases.label(tp), ["delegation:LOOP"])  # not the later block, which he did not name
        self.assertEqual([c["rule"] for c in lines(gatecases.SET)], ["LOOP"])
        add(h.assistant("Another false alarm."))  # no rule named: the latest unlabelled block, a single one
        self.assertEqual(gatecases.label(tp), ["delegation:TESTER-HERE"])

    def test_no_label_without_the_words_or_without_a_sent_block(self):
        tp, es = self.blocked_turn()
        self.assertIsNone(gatecases.label(tp))  # the reply does not say it
        other = h.transcript([h.user("x"), h.assistant("This was a false alarm.")])
        self.assertIsNone(gatecases.label(other))  # nothing was blocked in that session
        self.assertFalse(os.path.exists(gatecases.SET))


class Replay(unittest.TestCase):
    def test_the_seeds_pass_and_a_gate_without_its_vetoes_fails_them(self):
        cases = eval_gate.load()
        gaps = {c["id"] for c in cases if c.get("known_gap")}  # let through on purpose since the review-announced veto was removed
        self.assertEqual(gaps, {"seed-setup-manager-waits-for-review", "2026-11-16-reviewer-764810"})
        self.assertTrue(all(ok or cid in gaps for cid, ok, _ in eval_gate.run(cases)), [x for x in eval_gate.run(cases) if not x[1]])
        self.assertGreaterEqual(sum(c["expect"] == "no_block" for c in cases), 8)
        with mock.patch.object(delegvet, "veto", return_value=None):
            bad = [cid for cid, ok, _ in eval_gate.run(cases) if not ok]
        self.assertIn("seed-loop-with-no-failure", bad)
        self.assertIn("seed-reviewer-while-implementer-builds", bad)

    def test_the_real_brain_step_goes_through_the_same_vetoes(self):
        case = next(c for c in eval_gate.load() if c.get("scenario") and c["rule"] == "LOOP")
        brain.ask = h.brain_says("BLOCK LOOP | start round 2")
        self.assertEqual(eval_gate.run([case], real=True)[0][1:], (True, None))  # the brain asks for LOOP, no failure: vetoed
        self.assertIn("all 71", brain.ask.prompts[0] if brain.ask.prompts else "all 71 passed")


if __name__ == "__main__":
    unittest.main()
