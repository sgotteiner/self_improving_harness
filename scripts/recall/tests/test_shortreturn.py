"""SubagentStop short-return hook: a long final message is blocked once, a short one passes, a second stop passes, the
switch off passes, a missing message or a broken payload passes (fails open)."""
import json, unittest
from unittest import mock

import helpers as h
import ctx, shortreturn

LONG = "\n".join(f"line {i}" for i in range(shortreturn.MAX_LINES + 1))
SHORT = "\n".join(f"line {i}" for i in range(shortreturn.MAX_LINES))


def on(*s):
    return mock.patch.object(ctx, "enabled", side_effect=lambda x: x in s)


class Short(unittest.TestCase):
    def test_long_is_blocked_once(self):
        with on("short-returns"):
            o = json.loads(shortreturn.verdict({"last_assistant_message": LONG}))
            self.assertEqual(o["decision"], "block")
            self.assertIn("short summary", o["reason"])
            self.assertEqual(shortreturn.verdict({"last_assistant_message": LONG, "stop_hook_active": True}), "")

    def test_short_passes(self):
        with on("short-returns"):
            self.assertEqual(shortreturn.verdict({"last_assistant_message": SHORT}), "")

    def test_switch_off_passes(self):
        with on():
            self.assertEqual(shortreturn.verdict({"last_assistant_message": LONG}), "")

    def test_message_from_the_agent_transcript(self):
        tp = h.transcript([h.user("x"), h.assistant(LONG)])
        with on("short-returns"):
            self.assertIn("block", shortreturn.verdict({"agent_transcript_path": tp}))

    def test_no_message_fails_open(self):
        with on("short-returns"):
            self.assertEqual(shortreturn.verdict({}), "")
            self.assertEqual(shortreturn.verdict({"agent_transcript_path": "/nope"}), "")

    def test_slot_is_on_in_slots_json(self):
        self.assertTrue(json.load(open(ctx.ROOT + "/slots.json", encoding="utf-8"))["short-returns"]["enabled"])


if __name__ == "__main__":
    unittest.main()
