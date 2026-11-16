"""VISION.md is injected like a rule: first in every human message's hook output, and into every subagent's context
through a SubagentStart hook. Switch `vision` off -> nothing. A missing file never blocks (fails open)."""
import io, json, os, sys, tempfile, unittest
from unittest import mock

import helpers as h
import ctx, hook, vision

TEXT = "A setup that learns.\n\n**Rule:** keep this vision in mind before every action."


def vision_file(body="# Vision\n\n" + TEXT + "\n"):
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def enabled(*on):
    return mock.patch.object(ctx, "enabled", side_effect=lambda s: s in on)


def run_hook(prompt, *on, others=None):
    out = io.StringIO()
    tp = h.transcript([h.user("x"), h.assistant("ok")])
    with enabled(*on), mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"prompt": prompt, "transcript_path": tp}))), \
            mock.patch.object(sys, "stdout", out), mock.patch.dict(os.environ, {"RECALL_HOOK": "1"}):
        hook.main()
    return out.getvalue()


class Text(unittest.TestCase):
    def test_the_heading_is_dropped_and_the_rule_is_kept(self):
        with mock.patch.object(vision, "FILE", vision_file()):
            self.assertEqual(vision.text(), TEXT)
            self.assertNotIn("# Vision", vision.text())

    def test_the_real_vision_file_has_the_rule(self):
        t = vision.text()
        self.assertIn("keep this vision in mind before every action", t)
        self.assertFalse(t.startswith("#"))

    def test_a_missing_file_gives_nothing_and_no_error(self):
        with mock.patch.object(vision, "FILE", os.path.join(tempfile.gettempdir(), "no-such-vision.md")), enabled("vision"):
            self.assertEqual(vision.lines(), [])
            self.assertEqual(vision.subagent_output(), "")

    def test_editing_the_file_changes_what_is_injected(self):
        p = vision_file()
        with mock.patch.object(vision, "FILE", p), enabled("vision"):
            self.assertIn("A setup that learns.", vision.lines()[0])
            open(p, "w", encoding="utf-8").write("# Vision\n\nSomething else entirely.\n")
            self.assertEqual(vision.lines(), ["Something else entirely."])


class Main(unittest.TestCase):
    def test_the_hook_prints_the_vision_on_a_human_message(self):
        with mock.patch.object(vision, "FILE", vision_file()):
            out = run_hook("where is the map file", "vision")
        self.assertIn(TEXT, out)
        self.assertNotIn("# Vision", out)

    def test_switch_off_means_no_vision(self):
        with mock.patch.object(vision, "FILE", vision_file()):
            out = run_hook("where is the map file")
        self.assertNotIn("keep this vision", out)
        self.assertEqual(out.strip(), "")

    def test_the_vision_comes_before_every_other_line(self):
        with mock.patch.object(vision, "FILE", vision_file()), mock.patch.object(hook, "recall", return_value=["RECALL-LINE"]):
            out = run_hook("where is the map file", "vision", "recall-hook")
        self.assertIn("RECALL-LINE", out)
        self.assertLess(out.index("keep this vision"), out.index("RECALL-LINE"))

    def test_a_system_message_gets_no_vision(self):
        with mock.patch.object(vision, "FILE", vision_file()):
            out = run_hook("<task-notification>done</task-notification>", "vision")
        self.assertEqual(out.strip(), "")


class Subagents(unittest.TestCase):
    def test_the_subagent_hook_returns_the_vision_as_additional_context(self):
        with mock.patch.object(vision, "FILE", vision_file()), enabled("vision"):
            o = json.loads(vision.subagent_output())
        self.assertEqual(o["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        self.assertEqual(o["hookSpecificOutput"]["additionalContext"], TEXT)

    def test_switch_off_means_the_subagent_hook_outputs_nothing(self):
        with mock.patch.object(vision, "FILE", vision_file()), enabled():
            self.assertEqual(vision.subagent_output(), "")

    def test_settings_registers_the_hook_for_every_subagent(self):
        s = json.load(open(os.path.join(ctx.ROOT, "settings.json"), encoding="utf-8"))
        cmds = [x["command"] for g in s["hooks"]["SubagentStart"] for x in g["hooks"]]
        self.assertTrue(any(c.rstrip().endswith("vision.py subagent") for c in cmds), cmds)
        self.assertNotIn("matcher", s["hooks"]["SubagentStart"][0])  # no matcher: every agent type


if __name__ == "__main__":
    unittest.main()
