import os
import tempfile
import unittest
from pathlib import Path

from server.progress import write_progress


class ProgressTests(unittest.TestCase):
    def test_writes_dot_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_progress(50, 612, "encoded", tmp)
            text = Path(path).read_text(encoding="utf-8")
            self.assertEqual(text, "done=50\ntotal=612\nmsg=encoded\n")

    def test_pge_progress_dir_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["PGE_PROGRESS_DIR"] = tmp
            try:
                path = write_progress(1, 2, "split")
                self.assertEqual(Path(path).parent, Path(tmp))
            finally:
                del os.environ["PGE_PROGRESS_DIR"]


if __name__ == "__main__":
    unittest.main()
