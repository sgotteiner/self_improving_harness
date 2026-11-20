"""cases/stats.json counts per lesson: a gate catch recorded = correct, a gate block settled as false alarm = incorrect (the lesson
comes from the owed marker the gate left), a recorded correction repeat = missed; nothing else changes."""
import json, os, tempfile, unittest
from unittest import mock

import helpers as h
import capowed, capwrite, index

W = {"situation": "s", "did": "d", "disliked": "x", "lesson_id": "a-case"}


class Capstats(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.d, "cases"))
        open(os.path.join(self.d, "cases", "a-case.md"), "w", encoding="utf-8").write('---\nid: a-case\nlesson: "l"\n---\n')
        for o in (mock.patch.object(index, "CASES", os.path.join(self.d, "cases")), mock.patch.object(capwrite, "PENDING", os.path.join(self.d, "p")),
                  mock.patch.object(capowed, "OWED", os.path.join(self.d, "owed.json")), mock.patch.object(capwrite.history, "record")):
            o.start()
            self.addCleanup(o.stop)
        self.tp = h.transcript([h.user("x"), h.assistant("y")])

    def stats(self):
        p = os.path.join(self.d, "cases", "stats.json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

    def test_each_path_raises_only_its_own_count_by_one(self):
        self.assertEqual(self.stats(), {})
        capowed.owe("gate", self.tp, lesson="a-case")
        self.assertTrue(capwrite.write(dict(W, source="gate"))[0])
        self.assertEqual(self.stats(), {"a-case": {"correct": 1, "incorrect": 0, "missed": 0}})
        capowed.owe("gate", self.tp, lesson="a-case")
        self.assertTrue(capwrite.none("false alarm", "gate")[0])
        self.assertEqual(self.stats(), {"a-case": {"correct": 1, "incorrect": 1, "missed": 0}})
        self.assertTrue(capwrite.write(dict(W, his_words="again"))[0])
        self.assertEqual(self.stats(), {"a-case": {"correct": 1, "incorrect": 1, "missed": 1}})

    def test_nothing_counts_for_a_new_lesson_or_a_correction_false_alarm(self):
        self.assertTrue(capwrite.write({"situation": "s", "did": "d", "disliked": "x", "his_words": "w", "lesson": "l2", "slug": "new-one"})[0])
        capowed.owe("correction", self.tp, "p")
        self.assertTrue(capwrite.none("not a mistake")[0])
        self.assertEqual(self.stats(), {})

    def block(self, *ids):
        for i in ids:
            capowed.owe("gate", self.tp, lesson=i)

    def test_block_naming_two_lessons_settles_each_once(self):
        open(os.path.join(self.d, "cases", "b-case.md"), "w", encoding="utf-8").write('---\nid: b-case\nlesson: "l"\n---\n')
        self.block("a-case", "b-case")
        self.assertTrue(capwrite.write(dict(W, source="gate"))[0])
        self.assertTrue(capwrite.none("false alarm", "gate")[0])
        self.assertEqual(self.stats(), {"a-case": {"correct": 1, "incorrect": 0, "missed": 0}, "b-case": {"correct": 0, "incorrect": 1, "missed": 0}})

    def test_write_for_a_lesson_the_block_did_not_name_is_refused(self):
        open(os.path.join(self.d, "cases", "c-case.md"), "w", encoding="utf-8").write('---\nid: c-case\nlesson: "l"\n---\n')
        self.block("a-case", "b-case")
        ok, msg = capwrite.write(dict(W, source="gate", lesson_id="c-case"))
        self.assertFalse(ok)
        self.assertIn("a-case, b-case", msg)
        self.assertEqual(self.stats(), {})
        capwrite.history.record.assert_not_called()

    def test_corrupt_stats_file_is_left_alone(self):
        p = os.path.join(self.d, "cases", "stats.json")
        open(p, "w", encoding="utf-8").write("{broken")
        capowed.owe("gate", self.tp, lesson="a-case")
        self.assertTrue(capwrite.write(dict(W, source="gate"))[0])
        self.assertEqual(open(p, encoding="utf-8").read(), "{broken")

    def test_failed_count_does_not_fail_the_write(self):
        capowed.owe("gate", self.tp, lesson="a-case")
        with mock.patch.object(capwrite.capstats, "bump", side_effect=OSError("boom")):
            self.assertTrue(capwrite.write(dict(W, source="gate"))[0])
        capwrite.history.record.assert_called_once()


if __name__ == "__main__":
    unittest.main()
