"""The reviewer's probes of the labelling (only a first-person claim, only after the block, no case that contradicts a real block),
and the gate gaps the live labels found: an agent still running from an earlier turn, evidence sent to the implementer, a review
that asked for fixes, a quoted draft that is no claim."""
import json, os, tempfile, unittest

import helpers as h
import brain, delegate, delegvet, gatecases, turnfacts, verdicts
from test_delegate import step, ROOT

FEAT = dict(called=[], pending=[], claims=False, sm_ok=True, fell_short=False, review_open=False,
            round_started=False, suite_unexcused=False, edited=True, returned=False)


class Labels(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self._old = os.environ.get("RECALL_VERDICT_LOG"), gatecases.SET
        os.environ["RECALL_VERDICT_LOG"] = os.path.join(d, "v.jsonl")
        gatecases.SET = os.path.join(d, "set.jsonl")

    def tearDown(self):
        os.environ["RECALL_VERDICT_LOG"], gatecases.SET = self._old

    def blocked(self, rule="REVIEWER", **f):
        """A transcript with one sent delegation block logged at its end."""
        tp = h.transcript([h.user("x"), h.assistant("first")])
        self.add(tp, h.assistant("second"))
        verdicts.log(tp, "delegation", "BLOCK", rule, features=dict(FEAT, **f))
        verdicts.log(tp, "gate", "SENT")
        return tp

    def add(self, tp, *es):
        with open(tp, "a", encoding="utf-8") as f:
            f.writelines(json.dumps(e) + chr(10) for e in es)

    def labels(self):
        return [json.loads(l) for l in open(verdicts.path(), encoding="utf-8") if '"label"' in l]

    def test_a_negated_or_conditional_sentence_labels_nothing(self):
        tp = self.blocked()
        for say in ("This is not a false alarm; the reviewer was really missed.", "It was no false alarm.", "That isn't a false alarm.",
                    "If it were a false alarm I would say so.", "It could be a false alarm, but I am not sure.", "Whether this is a false alarm is open."):
            self.add(tp, h.assistant(say))
            self.assertIsNone(gatecases.label(tp), say)
        self.assertEqual(self.labels(), [])
        self.assertFalse(os.path.exists(gatecases.SET))
        self.add(tp, h.assistant("That block was a false alarm."))
        self.assertEqual(gatecases.label(tp), ["delegation:REVIEWER"])  # the first-person claim still works

    def test_a_sentence_never_labels_a_block_that_came_after_it(self):
        tp = self.blocked()
        self.add(tp, h.assistant("That was a false alarm."))
        self.assertEqual(gatecases.label(tp), ["delegation:REVIEWER"])
        self.add(tp, h.assistant("more work"))
        verdicts.log(tp, "delegation", "BLOCK", "TESTER", features=dict(FEAT, claims=True))  # a later, real block in the same turn
        verdicts.log(tp, "gate", "SENT")
        self.assertIsNone(gatecases.label(tp), "the earlier sentence is about the earlier block")
        self.assertEqual([r["rule"] for r in self.labels()], ["delegation:REVIEWER"])
        self.assertEqual([c["rule"] for c in map(json.loads, open(gatecases.SET, encoding="utf-8"))], ["REVIEWER"])

    def test_a_case_that_contradicts_a_real_block_is_not_added(self):
        real = dict(id="keep-x", rule="TESTER", expect="block", hedged=False, features=dict(FEAT, claims=True))
        open(gatecases.SET, "w", encoding="utf-8").write(json.dumps(real) + chr(10))
        block = dict(ts="2026-11-16T10:00:00", rule="TESTER", hedged=False, features=dict(FEAT, claims=True))
        self.assertIsNone(gatecases.add_case(block))
        self.assertEqual(len(open(gatecases.SET, encoding="utf-8").readlines()), 1)
        self.assertIsNotNone(gatecases.add_case(dict(block, features=dict(FEAT, claims=False, pending=["implementer"]))))  # other facts: a new case


class GateGaps(unittest.TestCase):
    def test_an_agent_still_running_from_an_earlier_turn_is_pending(self):
        es = [h.user("build it"), *h.launch("implementer", "i1", "t1"), h.assistant("started"), h.user("and now a draft"),
              h.assistant(h.tool("Edit", {"file_path": os.path.join(ROOT, "scripts", "a.py"), "old_string": "a", "new_string": "b"}), "Here is a draft of the vision file.")]
        t = turnfacts.turn(h.transcript(es), ROOT)
        self.assertEqual(t["pending"], ["implementer"])
        self.assertIsNone(step(es, "BLOCK TESTER | nothing tested")[0])
        returned = es[:4] + [h.notice("i1", "t1"), h.user("and now a draft")] + es[5:]
        self.assertEqual(turnfacts.turn(h.transcript(returned), ROOT)["pending"], [])  # its result came back in between
        self.assertEqual(step(returned, "BLOCK TESTER | nothing tested")[0][0], "TESTER")

    def test_evidence_sent_to_the_implementer_starts_the_round(self):
        fail = [h.user("x"), *h.launch("implementer", "i1", "t1"), h.notice("i1", "t1"), *h.launch("tester", "te", "t2"), h.notice("te", "t2", "FAILED (failures=2)")]
        self.assertEqual(step(fail + [h.assistant("It fell short.")], "BLOCK LOOP | start round 2")[0][0], "LOOP")
        sent = fail + [*h.resume("i1"), h.assistant("Sent the failing evidence to the implementer.")]
        self.assertIsNone(step(sent, "BLOCK LOOP | start round 2")[0])  # a SendMessage to the implementer is the round
        self.assertTrue(turnfacts.turn(h.transcript(sent), ROOT)["round_started"])

    def test_no_testing_or_documenting_while_the_review_asked_for_fixes(self):
        es = [h.user("go"), *h.launch("reviewer", "rv", "t4"), h.notice("rv", "t4", "Fix first: the state is saved before the write."), h.assistant("Reviewed.")]
        for kind in ("TESTER", "KNOWLEDGE-MANAGER"):
            self.assertIsNone(step(es, f"BLOCK {kind} | missing")[0], kind)

    def test_a_quoted_draft_is_no_claim_of_done(self):
        self.assertFalse(turnfacts.claims("Here is a draft:\n> A setup that keeps improving how it works with me. Ready for my projects."))
        self.assertTrue(turnfacts.claims("Fixed, it works now."))
        self.assertFalse(turnfacts.claims("It works with me on every project."))


if __name__ == "__main__":
    unittest.main()
