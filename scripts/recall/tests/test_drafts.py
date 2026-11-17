"""Drafts never interrupt him: no question on a normal message, one summary line on the first message of a day, none after;
a false capture is discarded only with a logged reason; the lesson draft's to-do line (capture.py used a function that did not exist)."""
import datetime, io, json, os, sys, tempfile, unittest
from unittest import mock

import helpers as h
import ctx, diary, drafts, hook, pending
from test_diary import Env, DIARY


class Quiet(Env):
    def setUp(self):
        super().setUp()
        self.lessons = os.path.join(self.d, "lessons")
        os.makedirs(self.lessons)
        open(os.path.join(self.lessons, "a-lesson.md"), "w").write("---\nid: a-lesson\nasked: false\n---\n")
        open(os.path.join(self.lessons, "b-lesson.md"), "w").write("---\nid: b-lesson\nasked: false\n---\n")
        self.draft()  # one diary draft (asked: false)
        drafts.LESSONS, drafts.STATE = self.lessons, os.path.join(self.d, "state")

    def message(self, prompt="go with option a please"):
        tp = h.transcript([h.user("x"), h.assistant("Done.")])
        out = io.StringIO()
        with mock.patch.object(ctx, "enabled", side_effect=lambda s: s in ("capture", "decision-capture")), \
                mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"prompt": prompt, "transcript_path": tp}))), mock.patch.object(sys, "stdout", out), \
                mock.patch("capture.process", return_value=None), mock.patch("decisions.process", return_value=None):
            hook.main()
        return out.getvalue()

    def test_a_normal_message_asks_nothing_and_the_first_one_of_the_day_gets_one_line(self):
        first = self.message()
        self.assertEqual(first.count("\n"), 1, first)  # one line
        self.assertIn("3 drafts waiting (2 lesson, 1 diary) - say 'review drafts' to see them", first)
        self.assertNotIn("Ask the owner exactly", first)
        self.assertNotIn("Add it?", first)
        for _ in range(3):
            self.assertEqual(self.message(), "", "nothing more the same day")

    def test_the_next_day_says_it_once_more_and_an_empty_day_says_nothing(self):
        today = datetime.date.today()
        self.assertEqual(len(drafts.daily_line(today)), 1)
        self.assertEqual(drafts.daily_line(today), [])
        self.assertEqual(len(drafts.daily_line(today + datetime.timedelta(days=1))), 1)
        for f in os.listdir(self.lessons):
            os.remove(os.path.join(self.lessons, f))
        os.remove(os.path.join(diary.PENDING, "new-one.md"))
        self.assertEqual(drafts.daily_line(today + datetime.timedelta(days=2)), [])  # nothing waits: no line

    def test_review_drafts_shows_every_draft_with_its_question(self):
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            drafts.show()
        self.assertIn("Diary (diary.md): New one", out.getvalue())  # asked or not, all of them

    def test_a_false_capture_is_discarded_only_with_a_logged_reason(self):
        flags = os.path.join(self.d, "FLAGS.md")
        open(flags, "w", encoding="utf-8").write("# Flags\n\n## Known debt (2026-11-15)\n- x\n")
        with mock.patch.object(diary, "flags_for", return_value=flags):
            self.assertEqual(drafts.discard("diary", "new-one", "his message was a question, not a decision"), 0)
            self.assertEqual(drafts.discard("lesson", "a-lesson", "he did not correct anything"), 0)
        self.assertFalse(os.path.exists(os.path.join(diary.PENDING, "new-one.md")))
        self.assertFalse(os.path.exists(os.path.join(self.lessons, "a-lesson.md")))
        self.assertTrue(os.path.exists(os.path.join(diary.PENDING, "_discarded", "new-one.md")), "kept, his words stay recoverable")
        self.assertIn('his_words: "w"', open(os.path.join(diary.PENDING, "_discarded", "new-one.md"), encoding="utf-8").read())
        self.assertTrue(os.path.exists(os.path.join(self.lessons, "_discarded", "a-lesson.md")))
        text = open(flags, encoding="utf-8").read()
        self.assertIn('discarded the diary draft `new-one` ("New one") as a false capture (his message was a question, not a decision)', text)
        self.assertIn('owner asked: "w"', text)  # the title and his quoted words
        self.assertIn("discarded the lesson draft `a-lesson`", text)
        self.assertTrue(text.index("Claude-on-its-own") < text.index("## Known debt"))
        self.assertNotIn("new-one", open(pending.TODO).read())  # its to-do line is gone with it
        self.assertEqual(drafts.waiting(), ([ "b-lesson"], []), "a discarded draft is not counted as waiting")
        import subprocess
        for f in ("cases/_pending/_discarded/x.md", "diary-pending/_discarded/x.md"):
            self.assertEqual(subprocess.run(["git", "-C", ctx.ROOT, "check-ignore", "-q", f]).returncode, 0, f)

    def test_a_discard_that_cannot_be_logged_or_has_no_reason_is_refused(self):
        self.draft("keep-me")
        with mock.patch.object(diary, "flags_for", return_value=""):
            self.assertEqual(drafts.discard("diary", "keep-me", "false"), 1)
        self.assertTrue(os.path.exists(os.path.join(diary.PENDING, "keep-me.md")))
        self.assertEqual(drafts.discard("diary", "keep-me", "  "), 2)
        self.assertEqual(drafts.discard("diary", "../x", "false"), 0)  # not a draft: nothing happens

    def test_a_written_lesson_gets_its_todo_line(self):
        import capwrite
        d = {"situation": "s", "did": "w", "disliked": "(not stated)", "his_words": "no", "lesson": "l", "slug": "keep-it-short"}
        with mock.patch.object(capwrite, "PENDING", os.path.join(self.d, "p")), mock.patch.object(capwrite.history, "record"):
            self.assertTrue(capwrite.write(d)[0])
        self.assertIn("review captured case `keep-it-short`", open(pending.TODO).read())


if __name__ == "__main__":
    unittest.main()
