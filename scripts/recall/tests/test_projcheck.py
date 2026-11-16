"""Project check on a first message: the five documents, the SDD format, the map, the hooks, once per session."""
import os, tempfile, unittest
from unittest import mock

import helpers as h
import ctx, projcheck


class ProjectCheck(unittest.TestCase):
    def project(self, claude, files=()):
        d = tempfile.mkdtemp()
        open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8").write(claude)
        for f, text in files:
            os.makedirs(os.path.dirname(os.path.join(d, f)), exist_ok=True)
            open(os.path.join(d, f), "w", encoding="utf-8").write(text)
        return d

    def test_missing_documents_and_an_inferred_why_are_listed(self):
        d = self.project("## Project documents\n- **SDD:** `sdd.md`\n- **Diary:** `docs/D.md`\n- **Ideas:** `docs/I.md`\n- **Tests:** **missing** - to be made\n",
                         [("docs/D.md", "**Why:** (inferred) x"), ("docs/I.md", "# i")])
        p = projcheck.check(d)
        self.assertIn("Tests: not listed or marked missing", p)
        self.assertIn("Todo: not listed or marked missing", p)
        self.assertTrue(any(x.startswith("SDD: listed but not found: sdd.md") for x in p), p)
        self.assertTrue(any("holds '(inferred)'" in x for x in p), p)

    def test_the_sdd_format_the_map_and_the_hooks_are_checked(self):
        good = open(os.path.join(ctx.ROOT, "skills", "sdd", "scripts", "fixtures", "good.md"), encoding="utf-8").read()
        docs = "## Project documents\n- **SDD:** `sdd.md`\n- **Diary:** `D.md`\n- **Ideas:** `I.md`\n- **Tests:** `T.md`\n- **Todo:** `todo.md`\n"
        rest = [(n, "# x") for n in ("D.md", "I.md", "T.md", "todo.md")]
        d = self.project(docs, [("sdd.md", "# Title\n\n## No fields here\n\ntext\n")] + rest)
        self.assertTrue(any("not in the sdd skill's format" in x for x in projcheck.check(d)))
        d = self.project(docs, [("sdd.md", good)] + rest)  # valid SDD, but not in git: no map is found
        p = projcheck.check(d)
        self.assertFalse(any("format" in x for x in p), p)

    def test_once_per_project_per_day_and_silent_when_clean_or_not_a_project(self):
        d = self.project("no documents section here\n")
        tp = h.transcript([h.user("x")], cwd=d)
        with mock.patch.object(projcheck, "STATE", tempfile.mkdtemp()):
            first = projcheck.first_message(tp, d)
            self.assertEqual(len(first), 1)
            self.assertIn("Project documents", first[0])
            self.assertEqual(projcheck.first_message(tp, d), [])  # once
            other = h.transcript([h.user("y")], cwd=d)
            self.assertEqual(projcheck.first_message(other, d), [])  # a new session the same day: still once
            self.assertEqual(projcheck.check(tempfile.mkdtemp()), [])  # a folder that is no project says nothing
            self.assertEqual(projcheck.first_message(tp, tempfile.mkdtemp()), [])

    def test_a_new_day_asks_again_and_removes_the_old_markers(self):
        d = self.project("no documents section here\n")
        tp = h.transcript([h.user("x")], cwd=d)
        state = tempfile.mkdtemp()
        with mock.patch.object(projcheck, "STATE", state):
            self.assertEqual(len(projcheck.first_message(tp, d)), 1)
            (marker,) = os.listdir(state)
            old = marker.replace(str(projcheck.datetime.date.today()), "2020-01-01")
            os.rename(os.path.join(state, marker), os.path.join(state, old))
            self.assertEqual(len(projcheck.first_message(tp, d)), 1)  # the old day's marker does not count
            self.assertEqual(os.listdir(state), [marker])  # and it was removed

    def test_the_marker_is_written_only_after_the_check_ran(self):
        d = self.project("no documents section here\n")
        tp = h.transcript([h.user("x")], cwd=d)
        state = tempfile.mkdtemp()
        with mock.patch.object(projcheck, "STATE", state), mock.patch.object(projcheck, "check", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                projcheck.first_message(tp, d)
        self.assertFalse(os.path.exists(state) and os.listdir(state), "a failed check must be tried again on the next message")

    def test_an_sdd_outside_git_gets_no_map_or_hook_advice(self):
        good = open(os.path.join(ctx.ROOT, "skills", "sdd", "scripts", "fixtures", "good.md"), encoding="utf-8").read()
        d = tempfile.mkdtemp()  # not a git repo
        open(os.path.join(d, "sdd.md"), "w", encoding="utf-8").write(good)
        self.assertEqual(projcheck.sdd_problems(os.path.join(d, "sdd.md")), [])

    def test_the_setups_own_documents_are_the_vault_files(self):
        self.assertEqual(projcheck.documents(os.path.normpath(ctx.ROOT)), projcheck.SETUP_DOCS)


if __name__ == "__main__":
    unittest.main()
