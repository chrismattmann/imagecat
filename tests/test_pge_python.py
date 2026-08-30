"""Python 3 sanity checks for ImageCat PGE scripts. No HuggingFace, no Solr."""

import ast
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PGE_BIN = os.path.join(ROOT, "pge", "src", "main", "resources", "bin")
sys.path.insert(0, os.path.join(PGE_BIN, "chunk_file"))

import chunk_file  # noqa: E402

_OCR_PATH = os.path.join(PGE_BIN, "imagecat-ocr", "imagecat-ocr.py")
_SPEC = importlib.util.spec_from_file_location("imagecat_ocr", _OCR_PATH)
ocr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ocr)


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


class TikaSolrMappingTests(unittest.TestCase):
    def test_content_type_field(self):
        self.assertEqual(ocr.solr_field_name("Content-Type"), "content_type")

    def test_exif_keys_become_solr_names(self):
        self.assertEqual(ocr.solr_field_name("tiff:Make"), "tiff_Make")
        self.assertEqual(ocr.solr_field_name("Exif IFD0:Date/Time"), "Exif_IFD0_Date_Time")

    def test_parse_skips_icc_and_keeps_camera(self):
        text = "\n".join([
            "Content-Type: image/jpeg",
            "tiff:Make: Canon",
            "Exif IFD0:Model: Canon EOS-1D X",
            "ICC:Green TRC: 0.0, 0.0000763, 0.0001526",
            "Padding: [2060 values]",
            "Color Halftoning Information: [72 values]",
            "By-line: Matteo Chinellato",
        ])
        parsed = ocr.parse_tika_metadata_text(text)
        self.assertEqual(parsed["content_type"], "image/jpeg")
        self.assertEqual(parsed["tiff_Make"], "Canon")
        self.assertEqual(parsed["Exif_IFD0_Model"], "Canon EOS-1D X")
        self.assertEqual(parsed["By_line"], "Matteo Chinellato")
        self.assertNotIn("ICC_Green_TRC", parsed)
        self.assertNotIn("Padding", parsed)
        self.assertFalse(any(k.startswith("ICC") for k in parsed))
        self.assertFalse(any("Halftoning" in k for k in parsed))


if __name__ == "__main__":
    unittest.main()
