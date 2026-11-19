"""graph.py: a lesson node per case, a path per history block (one block in two cases = one path to both lessons), a lesson
keeps its own text, a held-out path is left out, capture's match returns every lesson at or above SAME. Real embeddings."""
import os, tempfile, unittest
from unittest import mock

import ctx, graph, index

BLOCK = ("## 2026-11-01 | gate\n- situation: The assistant finished a fix and told him it works.\n- assistant did: It said the fix works "
         "without running any test this turn.\n- he did not like: A success claim with no run behind it.\n- lesson: {l}\n")


def case(d, cid, lesson, sit, hist):
    open(os.path.join(d, cid + ".md"), "w", encoding="utf-8").write(
        f"---\nid: {cid}\ndate: 2026-11-01\nlevel: advice\nsituation:\n  - {sit}\nwrong: wrong of {cid}\nright: right of {cid}\nlesson: {lesson}\n---\n")
    if hist:
        os.makedirs(os.path.join(d, "history"), exist_ok=True)
        open(os.path.join(d, "history", cid + ".md"), "w", encoding="utf-8").write("# h\n\n" + BLOCK.format(l=lesson))


class Graph(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        case(self.d, "claims", "Claim success only after a real run.", "he asks whether a change works", True)
        case(self.d, "scope", "Tell him what you will run before you run it.", "about to run a long job", True)
        case(self.d, "other", "Greet the owner politely in the morning.", "the owner says good morning", False)
        p = mock.patch.object(index, "CASES", self.d)
        p.start()
        self.addCleanup(p.stop)
        graph.reset()
        self.addCleanup(graph.reset)

    def test_one_block_in_two_histories_is_one_path_to_both_lessons(self):
        occ = graph.occurrences()
        self.assertEqual(len(occ), 1)
        self.assertEqual(sorted(occ[0]["lessons"]), ["claims", "scope"])
        hits = {c: p for _, c, p in graph.at_message("The assistant finished a fix and told him it works.", 3)}
        self.assertIs(hits["claims"], hits["scope"])
        self.assertEqual(graph.lesson("claims")["lesson"], "Claim success only after a real run.")
        self.assertEqual(graph.lesson("scope")["lesson"], "Tell him what you will run before you run it.")

    def test_held_out_path_is_not_a_source_of_either_lesson(self):
        key = graph.occurrences()[0]["key"]
        paths = [p for _, _, p in graph.at_reply("It said the fix works without running any test.", 3, {key})]
        self.assertTrue(all(p is None or p["key"] != key for p in paths))
        self.assertIn("Past:", graph.trace(graph.at_reply("It said the fix works without running any test.", 1)[0][2]))

    def test_match_returns_every_lesson_at_or_above_same(self):
        self.assertEqual([c for _, c in graph.match({"lesson": "Claim success only after a real run."})], ["claims"])
        self.assertEqual(graph.match({"lesson": "The sky is blue on clear days."}), [])

    def test_attach_modes_decide_how_many_lessons_a_repeat_attaches_to(self):
        parts = {"lesson": "Claim success only after a real run.", "action": "It said the fix works without running any test this turn."}
        ids = lambda: [c for _, c in graph.match(parts)]
        self.addCleanup(setattr, graph, "ATTACH", "all")
        for mode, want in (("all", ["claims", "scope"]), ("single", ["claims"]), ("agree", ["claims"])):  # scope shares only the action path
            graph.ATTACH = mode
            self.assertEqual(sorted(ids()), want, mode)
        graph.ATTACH = "agree"
        self.assertEqual(graph.match({"action": parts["action"]}), [])  # one kind alone is not enough

    def test_the_gate_shows_its_brain_the_matched_past_action_and_his_complaint(self):
        import brain, gate, helpers as h
        tp = h.transcript([h.user("x"), h.assistant("It said the fix works without running any test this turn.")])
        seen = []
        ask = lambda prompt, system="", tag="": (seen.append(prompt), ("VIOLATION claims | no run shown", 3))[1]
        with mock.patch.dict(os.environ, {"RECALL_VERDICT_LOG": os.path.join(self.d, "v.jsonl")}), mock.patch.object(ctx, "enabled", lambda slot: slot != "recall-all-lessons"), \
                mock.patch.object(brain, "ask", ask), mock.patch.object(index, "meta", return_value=("2026-11-01", "s", "l", "r")):
            self.assertEqual(gate.check(tp), [("claims", "no run shown")])
        self.assertIn("A success claim with no run behind it", seen[0])
        self.assertIn("It said the fix works without running any test this turn", seen[0])


if __name__ == "__main__":
    unittest.main()
