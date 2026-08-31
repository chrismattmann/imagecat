import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from server.index_lock import LOCK_NAME, exclusive_index

ROOT = str(Path(__file__).resolve().parents[1])

_CHILD = r"""
import sys, time
from pathlib import Path
from server.index_lock import exclusive_index
folder, hold, marker = sys.argv[1], float(sys.argv[2]), sys.argv[3]
with exclusive_index(folder):
    time.sleep(hold)
    Path(marker).write_text("done")
"""


def _run(folder, hold, marker):
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.Popen(
        [sys.executable, "-c", _CHILD, folder, str(hold), marker],
        env=env,
        cwd=ROOT,
    )


class IndexLockTests(unittest.TestCase):
    def test_creates_lockfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            with exclusive_index(tmp) as folder:
                self.assertTrue((Path(folder) / LOCK_NAME).is_file())

    def test_second_process_waits(self):
        with tempfile.TemporaryDirectory() as tmp:
            first_mark = str(Path(tmp) / "first")
            second_mark = str(Path(tmp) / "second")
            first = _run(tmp, 0.5, first_mark)
            time.sleep(0.15)
            t0 = time.time()
            second = _run(tmp, 0.0, second_mark)
            self.assertEqual(second.wait(timeout=5), 0)
            waited = time.time() - t0
            self.assertEqual(first.wait(timeout=5), 0)
            self.assertEqual(Path(second_mark).read_text(), "done")
            self.assertGreaterEqual(waited, 0.25)


if __name__ == "__main__":
    unittest.main()
