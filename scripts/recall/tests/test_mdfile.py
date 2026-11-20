"""The lock file: a stale one is broken safely when several wait, and releasing never raises."""
import os, tempfile, threading, time, unittest
from unittest import mock

import mdfile


class Lock(unittest.TestCase):
    def setUp(self):
        self.lock = os.path.join(tempfile.mkdtemp(), "x.lock")

    def stale(self):
        open(self.lock, "w").close()
        os.utime(self.lock, (time.time() - 60, time.time() - 60))

    def test_two_waiters_on_a_stale_lock_never_hold_it_together(self):
        self.stale()
        inside, worst, done = [0], [0], []

        def work():
            with mdfile.held(self.lock) as got:
                if got:
                    inside[0] += 1
                    worst[0] = max(worst[0], inside[0])
                    time.sleep(0.02)
                    inside[0] -= 1
                done.append(got)
        ts = [threading.Thread(target=work) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual((worst[0], done), (1, [True] * 6))
        self.assertEqual(os.listdir(os.path.dirname(self.lock)), [])  # no lock and no renamed stale file left behind

    def test_a_fresh_lock_taken_between_the_check_and_the_rename_is_given_back(self):
        open(self.lock, "w").close()  # fresh
        mdfile._break_stale(self.lock)
        self.assertTrue(os.path.exists(self.lock))
        self.assertEqual(os.listdir(os.path.dirname(self.lock)), ["x.lock"])

    def test_releasing_a_lock_that_is_already_gone_does_not_raise(self):
        with mdfile.held(self.lock) as got:
            self.assertTrue(got)
            os.remove(self.lock)  # a waiter broke it as stale


if __name__ == "__main__":
    unittest.main()
