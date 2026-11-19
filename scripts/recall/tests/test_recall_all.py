"""hook.recall with the recall-all-lessons slot on: one brain call with every lesson; only the ids the model names print."""
import unittest
from unittest import mock

import ctx, hook, alllessons, brain


class RecallAll(unittest.TestCase):
    def test_one_call_with_all_lessons_prints_only_the_named_ids(self):
        ids = list(alllessons.lessons())
        ans = f"{ids[0]} | he asks to test\n{ids[2]} | no run shown\nnot-a-lesson | x"
        with mock.patch.object(ctx, "enabled", side_effect=lambda s: s == "recall-all-lessons"), mock.patch.object(ctx, "recent", return_value=[]), \
                mock.patch.object(brain, "ask", return_value=(ans, 1)) as ask:
            lines = hook.recall("please run the tests now", "tp")
        self.assertEqual(ask.call_count, 1)
        self.assertTrue(all(c in ask.call_args[0][0] for c in ids))
        self.assertEqual(len(lines), 2)
        self.assertIn(f"cases/{ids[0]}.md", lines[0])
        self.assertIn(f"cases/{ids[2]}.md", lines[1])


if __name__ == "__main__":
    unittest.main()
