"""A second index job waits for the first, rather than failing.

The lock exists because two --incremental jobs rewrite the same snapshot
files: both load the same ids, encode overlapping images, and the last
save_index wins, dropping the other job's vectors. Waiting is the whole
behaviour -- on a full run the fg/bg stage holds the lock for the better
part of an hour.

portalocker's timeout=None does not mean "no timeout". It falls back to
the library default of five seconds and then raises AlreadyLocked, so the
obvious translation of the old fcntl code turned "wait your turn" into
"fail after five seconds".
"""

import os
import subprocess
import sys
import textwrap
import time
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER = os.path.join(ROOT, "imagespace", "server")

HOLDER = """
import sys, time
sys.path.insert(0, {server!r})
from index_lock import exclusive_index
with exclusive_index({folder!r}):
    print("held", flush=True)
    time.sleep({seconds})
"""

WAITER = """
import sys, time
sys.path.insert(0, {server!r})
from index_lock import exclusive_index
start = time.time()
with exclusive_index({folder!r}):
    print("waited %.1f" % (time.time() - start), flush=True)
"""


def script(template, folder, seconds=0):
    return textwrap.dedent(
        template.format(server=SERVER, folder=folder, seconds=seconds))


class IndexLockWaits(unittest.TestCase):

    def setUp(self):
        try:
            import portalocker  # noqa: F401
        except ImportError:
            self.skipTest("portalocker is not installed")
        import tempfile
        self.folder = tempfile.mkdtemp()

    def test_a_second_job_waits_instead_of_failing(self):
        hold = subprocess.Popen(
            [sys.executable, "-c", script(HOLDER, self.folder, seconds=7)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual("held", hold.stdout.readline().strip())

        waiter = subprocess.run(
            [sys.executable, "-c", script(WAITER, self.folder)],
            capture_output=True, text=True, timeout=60)
        hold.wait(timeout=30)

        self.assertEqual(0, waiter.returncode,
                         "the second job failed instead of waiting:\n"
                         + waiter.stderr)
        # It must actually have waited for the holder, not slipped past it.
        waited = float(waiter.stdout.strip().split()[1])
        self.assertGreater(waited, 3.0,
                           "acquired too quickly to have waited for the lock")

    def test_the_wait_is_announced(self):
        # A job blocked behind an hour-long fg/bg run is indistinguishable
        # from one that has hung unless it says so.
        hold = subprocess.Popen(
            [sys.executable, "-c", script(HOLDER, self.folder, seconds=6)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual("held", hold.stdout.readline().strip())

        waiter = subprocess.run(
            [sys.executable, "-c", script(WAITER, self.folder)],
            capture_output=True, text=True, timeout=60)
        hold.wait(timeout=30)

        self.assertIn("waiting for index lock", waiter.stderr)

    def test_an_uncontended_lock_is_immediate_and_quiet(self):
        done = subprocess.run(
            [sys.executable, "-c", script(WAITER, self.folder)],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertNotIn("waiting for index lock", done.stderr)
        self.assertLess(float(done.stdout.strip().split()[1]), 1.0)


if __name__ == "__main__":
    unittest.main()
