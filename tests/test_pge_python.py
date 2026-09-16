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
            os.path.join(PGE_BIN, "check_failed", "check_failed.py"),
            os.path.join(PGE_BIN, "imagecat-ocr", "imagecat-ocr.py"),
        ]
        for path in scripts:
            with open(path, encoding="utf-8") as handle:
                ast.parse(handle.read(), filename=path)

    def test_index_imagespace_skips_without_home(self):
        import subprocess

        env = os.environ.copy()
        env.pop("IMAGE_SPACE_HOME", None)
        env.pop("IMAGE_SPACE_PYTHON", None)
        env.pop("OODT_HOME", None)
        env.pop("IMAGECAT_HOME", None)
        for name in ("index-imagespace", "index-imagespace-fgbg", "index-metadata-jaccard"):
            script = os.path.join(PGE_BIN, name, name + ".sh")
            out = subprocess.check_output(["bash", script], env=env, text=True)
            self.assertIn("skip", out)

    def test_chunkfile_extractor_labels_are_imagecat(self):
        path = os.path.join(
            ROOT, "pge", "src", "main", "resources",
            "extractors", "filename", "chunkfile_extractor.xml",
        )
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("ImageCat Filename Met Extractor", text)
        self.assertIn("<scalar name=\"DataProvider\">ImageCat</scalar>", text)
        self.assertNotIn("OODT Filename Met Extractor", text)
        self.assertNotIn("<scalar name=\"DataProvider\">OODT</scalar>", text)


class PaddleOcrResultTests(unittest.TestCase):
    def test_empty_when_detector_finds_nothing(self):
        self.assertEqual(ocr.texts_from_paddle(None), "")
        self.assertEqual(ocr.texts_from_paddle((None, None)), "")
        self.assertEqual(ocr.texts_from_paddle([]), "")
        class Empty:
            txts = ()
        self.assertEqual(ocr.texts_from_paddle(Empty()), "")

    def test_joins_rapidocr_txts(self):
        class Out:
            txts = ("HELLO", "WORLD")
        self.assertEqual(ocr.texts_from_paddle(Out()), "HELLO\nWORLD")

    def test_joins_legacy_box_text_score(self):
        rows = [[[0, 0], [1, 0], [1, 1], [0, 1]], "CASHIER", 0.99]
        self.assertEqual(ocr.texts_from_paddle([rows]), "CASHIER")

    def test_paddle_is_a_model_choice(self):
        self.assertEqual(ocr.PADDLE_MODEL, "rapidocr/pp-ocr")


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


class TikaBatchTests(unittest.TestCase):
    """Tika costs about half a second per process before it reads an image.

    Paid per file that is most of the stage; paid per batch it is nothing.
    Measured on twenty 8MB JPEGs: 29.7s one at a time, 18.8s batched.
    """

    def test_stream_splits_concatenated_objects(self):
        # tika-app -j writes one object per input with nothing between them,
        # so the output is a stream rather than a list.
        text = '{"resourceName":"a.jpg","tiff:Make":"Canon"}' \
               '{"resourceName":"b.jpg","tiff:Make":"Nikon"}'
        out = ocr.parse_tika_json_stream(text)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["resourceName"], "a.jpg")
        self.assertEqual(out[1]["tiff:Make"], "Nikon")

    def test_stream_tolerates_whitespace_and_newlines(self):
        text = '\n{"resourceName":"a.jpg"}\n\n{"resourceName":"b.jpg"}\n'
        self.assertEqual(len(ocr.parse_tika_json_stream(text)), 2)

    def test_stream_stops_at_garbage_rather_than_raising(self):
        # A truncated batch must not take the run down; the caller checks the
        # count and falls back.
        text = '{"resourceName":"a.jpg"}{"resourceName":'
        self.assertEqual(len(ocr.parse_tika_json_stream(text)), 1)

    def test_clean_applies_the_same_filters_as_the_line_parser(self):
        raw = {
            "Content-Type": "image/jpeg",
            "tiff:Make": "Canon",
            "ICC:Green TRC": "0.0, 0.0000763",
            "Padding": "x",
            "By-line": "Matteo Chinellato",
        }
        parsed = ocr.clean_tika_fields(raw)
        self.assertEqual(parsed["content_type"], "image/jpeg")
        self.assertEqual(parsed["tiff_Make"], "Canon")
        self.assertEqual(parsed["By_line"], "Matteo Chinellato")
        self.assertNotIn("Padding", parsed)
        self.assertFalse(any(k.startswith("ICC") for k in parsed))

    def test_clean_takes_the_first_of_a_multi_valued_field(self):
        # JSON gives lists where the line format gave one line.
        self.assertEqual(
            ocr.clean_tika_fields({"tiff:Make": ["Canon", "Canon"]})["tiff_Make"],
            "Canon")

    def test_clean_drops_the_fields_that_would_collide_with_our_own(self):
        raw = {"id": "x", "ocr_text": "y", "sha1sum_s_md": "z", "tiff:Make": "Canon"}
        parsed = ocr.clean_tika_fields(raw)
        self.assertEqual(list(parsed), ["tiff_Make"])

    def test_a_json_caption_with_html_stays_one_field(self):
        # The line parser split IPTC captions containing markup into invented
        # fields -- B_Ref, Picture_by, Pictured -- and truncated the caption at
        # the first newline. Parsed as JSON the caption survives whole.
        caption = "Awards at 72nd Venice\n<B>Ref: SPL1123870</B><BR/>\nPicture by: Splash"
        parsed = ocr.clean_tika_fields({"Caption/Abstract": caption})
        self.assertEqual(len(parsed), 1)
        self.assertNotIn("B_Ref", parsed)
        self.assertNotIn("Picture_by", parsed)
        self.assertIn("Awards at 72nd Venice", parsed["Caption_Abstract"])

    def test_batch_size_is_bounded(self):
        # The paths go on a command line, and ARG_MAX is finite.
        self.assertGreater(ocr.TIKA_BATCH, 1)
        self.assertLessEqual(ocr.TIKA_BATCH, 1000)

    def test_no_tika_returns_one_empty_dict_per_path(self):
        self.assertEqual(ocr.tika_metadata_batch(["a", "b"], None), [{}, {}])

    def test_empty_batch_is_not_an_error(self):
        self.assertEqual(ocr.tika_metadata_batch([], None), [])


if __name__ == "__main__":
    unittest.main()
