"""gate.py: a hedging lesson verdict is dropped; several broken lessons come in one block, with every lesson sent."""
import io, json, sys, unittest
from unittest import mock

import ctx, gate


def run(lesson, delegation):
    out = io.StringIO()
    with mock.patch.object(gate, "check", return_value=[lesson] if lesson else None), mock.patch.object(gate, "delegation", return_value=delegation), \
            mock.patch.object(ctx, "enabled", side_effect=lambda s: s == "output-gate"), mock.patch.object(sys, "stdin", io.StringIO('{"transcript_path": "x"}')), \
            mock.patch.object(sys, "stdout", out):
        gate.main()
    return json.loads(out.getvalue()) if out.getvalue() else None


class Gate(unittest.TestCase):
    def test_a_lesson_verdict_that_leads_with_a_hedge_does_not_block(self):
        self.assertIsNone(run(("c", "This may be OK: it claims it works"), None))
        self.assertIsNotNone(run(("c", "Claims it works with no run; unclear which file, run the test"), None))

    def test_all_lessons_slot_names_several_violations_in_one_block(self):
        import alllessons, brain
        ids = list(alllessons.lessons())[:2]
        ans = "\n".join(f"VIOLATION {c} | broke {c}, fix it" for c in ids)
        with mock.patch.object(ctx, "enabled", side_effect=lambda s: s == "recall-all-lessons"), mock.patch.object(gate.verdicts, "log"), \
                mock.patch.object(ctx, "last_turn", return_value=("done, works", [])), mock.patch.object(brain, "ask", return_value=(ans, 1)) as ask:
            found = gate.check("x")
        self.assertEqual([c for c, _ in found], ids)
        self.assertEqual(ask.call_count, 1)
        self.assertTrue(all(c in ask.call_args[0][0] for c in alllessons.lessons()))  # every lesson was sent
        with mock.patch.object(gate, "check", return_value=found), mock.patch.object(gate, "delegation", return_value=None), \
                mock.patch.object(ctx, "enabled", side_effect=lambda s: s == "output-gate"), mock.patch.object(sys, "stdin", io.StringIO('{"transcript_path": "x"}')), \
                mock.patch.object(sys, "stdout", io.StringIO()) as out:
            gate.main()
        reason = json.loads(out.getvalue())["reason"]
        self.assertTrue(all(f"cases/{c}.md" in reason for c in ids))

if __name__ == "__main__":
    unittest.main()
