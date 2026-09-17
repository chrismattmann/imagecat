"""Tika is asked for MIME type and EXIF, and told not to OCR.

Tika detects tesseract on the PATH and, from 2.x on, runs it over every
image it parses. ImageCat does its own OCR with RapidOCR and keeps that, so
tesseract's answer is computed and thrown away. Nothing announces it: the
stage just gets slower, and the java process shows almost no CPU because
the work is in a subprocess.

On this machine tesseract arrived in June 2025 as a dependency of
ghostscript, years after the OCR stage was written and with no connection
to it. So the trigger is not a change to this repository at all, which is
why it has to be turned off explicitly rather than merely not asked for.

Measured on the corpus: 0.25s per image with it, 0.09s without.

These tests call the argument builder and capture the argv actually handed
to the JVM, rather than grepping for the flag.
"""

import importlib.util
import os
import sys
import types
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PGE_BIN = os.path.join(ROOT, "pge", "src", "main", "resources", "bin")
OCR_PATH = os.path.join(PGE_BIN, "imagecat-ocr", "imagecat-ocr.py")
CONFIG = os.path.join(PGE_BIN, "imagecat-ocr", "tika-no-ocr.xml")
PGE_ASSEMBLY = os.path.join(ROOT, "pge", "src", "main", "assembly",
                            "assembly.xml")


def load_ocr():
    if "pysolr" not in sys.modules:
        fake = types.ModuleType("pysolr")
        fake.Solr = object
        sys.modules["pysolr"] = fake
    spec = importlib.util.spec_from_file_location("imagecat_ocr_tika_test",
                                                  OCR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Recorder:
    """Stands in for subprocess.run and keeps the argv it was given."""

    def __init__(self, stdout="", returncode=0):
        self.calls = []
        self._stdout = stdout
        self._returncode = returncode

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        return types.SimpleNamespace(args=argv, returncode=self._returncode,
                                     stdout=self._stdout, stderr="")


class TheConfigSaysNoToTesseract(unittest.TestCase):
    def test_it_exists_next_to_the_script_that_uses_it(self):
        # Shipped rather than written at runtime, so the file the tests read
        # is the file Tika is given.
        self.assertTrue(os.path.isfile(CONFIG), CONFIG)

    def test_it_is_well_formed(self):
        ET.parse(CONFIG)

    def test_it_excludes_the_tesseract_parser_from_the_default_parser(self):
        root = ET.parse(CONFIG).getroot()
        parsers = root.findall("./parsers/parser")
        self.assertEqual(1, len(parsers))
        self.assertEqual("org.apache.tika.parser.DefaultParser",
                         parsers[0].get("class"),
                         "the exclusion has to hang off DefaultParser, or "
                         "Tika keeps its whole default registry and the "
                         "exclusion is ignored")
        excluded = [e.get("class")
                    for e in parsers[0].findall("parser-exclude")]
        self.assertIn("org.apache.tika.parser.ocr.TesseractOCRParser",
                      excluded)


class TheFlagReachesTheJvm(unittest.TestCase):
    def setUp(self):
        self.ocr = load_ocr()
        self.expected = "--config=%s" % self.ocr.TIKA_CONFIG

    def test_the_builder_points_at_the_shipped_config(self):
        self.assertEqual([self.expected], self.ocr.tika_config_args())
        self.assertTrue(os.path.isfile(str(self.ocr.TIKA_CONFIG)))

    def test_the_batch_call_carries_it(self):
        rec = _Recorder(stdout="[]")
        self.ocr.subprocess.run = rec
        self.ocr.tika_metadata_batch(["/a.jpg", "/b.jpg"], "/tmp/tika-app.jar")
        self.assertTrue(rec.calls, "Tika was never invoked")
        self.assertIn(self.expected, rec.calls[0])

    def test_the_single_file_call_carries_it_too(self):
        # The batch falls back to this one file at a time, so a flag on only
        # the batch is a flag that disappears exactly when things go wrong.
        rec = _Recorder(stdout="")
        self.ocr.subprocess.run = rec
        self.ocr.tika_metadata("/a.jpg", "/tmp/tika-app.jar")
        self.assertTrue(rec.calls)
        self.assertIn(self.expected, rec.calls[0])

    def test_the_path_to_parse_stays_last(self):
        rec = _Recorder(stdout="")
        self.ocr.subprocess.run = rec
        self.ocr.tika_metadata("/a.jpg", "/tmp/tika-app.jar")
        self.assertEqual("/a.jpg", rec.calls[0][-1])

    def test_every_path_still_reaches_the_batch(self):
        rec = _Recorder(stdout="[]")
        self.ocr.subprocess.run = rec
        paths = ["/a.jpg", "/b with space.jpg", "/c.jpg"]
        self.ocr.tika_metadata_batch(paths, "/tmp/tika-app.jar")
        for path in paths:
            self.assertIn(path, rec.calls[0])

    def test_a_missing_config_is_slow_not_broken(self):
        # A deployment assembled by hand may not have the file. Tika then
        # uses its defaults: the stage is slow, which is what it was before.
        self.ocr.TIKA_CONFIG = self.ocr.Path("/nonexistent/tika-no-ocr.xml")
        self.assertEqual([], self.ocr.tika_config_args())


class TheConfigIsPackaged(unittest.TestCase):
    def test_the_pge_assembly_ships_everything_under_bin(self):
        # pge/src/main/resources/bin -> pge/bin with no <includes> filter, so
        # the config travels with the script. A filter added here later that
        # names *.py would leave the script asking for a file that is not
        # there.
        root = ET.parse(PGE_ASSEMBLY).getroot()
        ns = {"a": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
        sets = root.iter("{%s}fileSet" % ns["a"]) if ns else root.iter("fileSet")
        for fs in sets:
            def kid(name):
                tag = "{%s}%s" % (ns["a"], name) if ns else name
                return fs.find(tag)
            directory = kid("directory")
            if directory is None or not directory.text.endswith("resources/bin"):
                continue
            includes = kid("includes")
            self.assertTrue(
                includes is None or len(list(includes)) == 0,
                "pge/bin is filtered; tika-no-ocr.xml would not be packaged")
            return
        self.fail("no fileSet for pge/src/main/resources/bin")


if __name__ == "__main__":
    unittest.main()
