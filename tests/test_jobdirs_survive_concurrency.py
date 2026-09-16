"""Job directories under a queue-based engine that runs tasks at once.

W1's thread pool effectively serialised these tasks, so a JobDir keyed on
milliseconds almost never collided. W2 runs eight at a time: on the first
seven-chunk run, six of thirteen IngestInPlace tasks died with

    mkdir: .../data/jobs/crawl/1789575989719/output: File exists

because two chunks started in the same millisecond and were handed the same
directory. The second one's mkdir failed and took the task with it.

Two separate problems, so two separate guards: the mkdir should not care
whether the directory exists, and two concurrent chunks should not be given
the same directory in the first place -- sharing one would mix their
outputs, and the receipt that OcrSettled counts is one of those outputs.
"""

import glob
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POLICY = os.path.join(ROOT, "pge", "src", "main", "resources", "policy")


def configs():
    return sorted(glob.glob(os.path.join(POLICY, "PgeConfig_*.xml")))


def body(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class MkdirDoesNotCareIfTheDirectoryExists(unittest.TestCase):
    def test_no_bare_mkdir_in_any_pge_config(self):
        offenders = []
        for path in configs():
            for cmd in re.findall(r"<cmd>([^<]*mkdir[^<]*)</cmd>", body(path)):
                for piece in cmd.split(";"):
                    piece = piece.strip()
                    if piece.startswith("mkdir ") and not piece.startswith("mkdir -p"):
                        offenders.append("%s: %s" % (os.path.basename(path), piece))
        self.assertEqual(offenders, [],
                         "a bare mkdir fails the task when the directory is "
                         "already there: %s" % offenders)


class ConcurrentChunksGetDifferentDirectories(unittest.TestCase):
    # The configs whose tasks run once per chunk, and therefore at the same
    # time as each other.
    PER_CHUNK = ("PgeConfig_Crawl.xml", "PgeConfig_Ocr.xml")

    def jobdir(self, path):
        found = re.search(r'key="JobDir"\s+val="([^"]*)"', body(path))
        self.assertTrue(found, "%s has no JobDir" % os.path.basename(path))
        return found.group(1)

    def test_per_chunk_jobdirs_are_not_keyed_on_time_alone(self):
        for name in self.PER_CHUNK:
            path = os.path.join(POLICY, name)
            val = self.jobdir(path)
            self.assertIn("[ChunkNum]", val,
                          "%s keys its JobDir on %s; two chunks starting in "
                          "the same millisecond would share it" % (name, val))

    def test_every_pge_jobdir_has_something_time_based(self):
        # Uniqueness across runs, not just within one.
        for path in configs():
            val = self.jobdir(path)
            self.assertIn("[DateMilis]", val, os.path.basename(path))


if __name__ == "__main__":
    unittest.main()
