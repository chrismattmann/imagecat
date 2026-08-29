"""Python 3 sanity checks for ImageCat PGE scripts. No HuggingFace, no Solr."""

import ast
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PGE_BIN = os.path.join(ROOT, "pge", "src", "main", "resources", "bin")
sys.path.insert(0, os.path.join(PGE_BIN, "chunk_file"))

import chunk_file  # noqa: E402


class ChunkFileTests(unittest.TestCase):
    def test_splits_into_named_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing = os.path.join(tmp, "all.txt")
            with open(listing, "w", encoding="utf-8") as handle:
                handle.write("\n".join("/data/img-%d.jpg" % i for i in range(5)))
                handle.write("\n")
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                n = chunk_file.split_and_execute(listing, 2)
            finally:
                os.chdir(cwd)
            self.assertEqual(n, 3)
            first = os.path.join(tmp, "filelist_chunk_0.txt")
            with open(first, encoding="utf-8") as handle:
                lines = [line.strip() for line in handle if line.strip()]
            self.assertEqual(lines, ["/data/img-0.jpg", "/data/img-1.jpg"])

    def test_scripts_parse_as_python3(self):
        scripts = [
            os.path.join(PGE_BIN, "chunk_file", "chunk_file.py"),
            os.path.join(PGE_BIN, "sha1sum", "sha1sum.py"),
            os.path.join(PGE_BIN, "check_failed", "check_failed.py"),
            os.path.join(PGE_BIN, "imagecat-ocr", "imagecat-ocr.py"),
        ]
        for path in scripts:
            with open(path, encoding="utf-8") as handle:
                ast.parse(handle.read(), filename=path)


if __name__ == "__main__":
    unittest.main()
