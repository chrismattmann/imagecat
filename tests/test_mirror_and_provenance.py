"""The id is the file on disk; where it came from is a field.

ImageSpace reads the catalogued file on every first view. On an external
volume that is about 47 MB/s here against 3258 MB/s locally, so `imagecat
index` mirrors the source under IMAGECAT_HOME by default and catalogues the
mirror. --no-mirror indexes the source directly and accepts its read speed.

Either way the id is the absolute path of the file that was catalogued, so
opening the id gets the bytes with nothing to derive. Provenance is recorded
instead of implied: orig_path and mirror_path carry the pair.

#84 removed an earlier copy because the id was the copy's path and the
original was nowhere on the record. The original is on the record now, and
the mirror path is a pure function of the source, so the id no longer
depends on what was staged before it or in what order -- which is what
actually made the old scheme's ids unusable.
"""

import importlib.util
import os
import re
import subprocess
import sys
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGECAT = os.path.join(ROOT, "distribution", "src", "main", "resources",
                        "bin", "imagecat")
PGE_BIN = os.path.join(ROOT, "pge", "src", "main", "resources", "bin")
OCR_PATH = os.path.join(PGE_BIN, "imagecat-ocr", "imagecat-ocr.py")
SCHEMA = os.path.join(ROOT, "solr", "src", "main", "resources", "imagecat",
                      "conf", "schema.xml")


def body(path=IMAGECAT):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def extract(name):
    text = body()
    start = text.index("\n%s() {\n" % name) + 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("%s() is not closed" % name)


def mirror_path_for(source, home="/srv/imagecat"):
    script = "%s\n%s\nIMAGECAT_HOME=%s\nmirror_path_for '%s'\n" % (
        extract("mirror_root"), extract("mirror_path_for"), home, source)
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


def load_ocr():
    if "pysolr" not in sys.modules:
        fake = types.ModuleType("pysolr")
        fake.Solr = object
        sys.modules["pysolr"] = fake
    spec = importlib.util.spec_from_file_location("imagecat_ocr_mirror_test",
                                                  OCR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheMirrorPathIsAFunctionOfTheSource(unittest.TestCase):
    def test_the_source_hangs_under_the_mirror_root(self):
        code, path = mirror_path_for("/Volumes/BRICK/pics/a.jpg")
        self.assertEqual(0, code)
        self.assertEqual(
            "/srv/imagecat/data/staging/images/Volumes/BRICK/pics/a.jpg", path)

    def test_the_same_source_always_mirrors_to_the_same_place(self):
        # The property that lets a mirror path be an id at all. The scheme
        # this replaces appended -2, -3 depending on what had been staged
        # before, so the same image could take two different ids.
        first = mirror_path_for("/Volumes/BRICK/pics/a.jpg")
        second = mirror_path_for("/Volumes/BRICK/pics/a.jpg")
        self.assertEqual(first, second)

    def test_two_volumes_sharing_a_layout_do_not_collide(self):
        _, one = mirror_path_for("/Volumes/ONE/pics")
        _, two = mirror_path_for("/Volumes/TWO/pics")
        self.assertNotEqual(one, two)

    def test_a_path_with_spaces_survives(self):
        _, path = mirror_path_for("/Volumes/BRICK/Images for Chris/a.jpg")
        self.assertTrue(path.endswith("/Volumes/BRICK/Images for Chris/a.jpg"),
                        path)


class ProvenanceIsRecovered(unittest.TestCase):
    """provenance(), executed, against the mirror rule the shell uses."""

    def setUp(self):
        self.ocr = load_ocr()
        os.environ["IMAGECAT_MIRROR_ROOT"] = "/srv/imagecat/data/staging/images"

    def tearDown(self):
        os.environ.pop("IMAGECAT_MIRROR_ROOT", None)

    def test_a_mirrored_file_reports_both_paths(self):
        mirrored = "/srv/imagecat/data/staging/images/Volumes/BRICK/pics/a.jpg"
        self.assertEqual(
            {"orig_path": "/Volumes/BRICK/pics/a.jpg",
             "mirror_path": mirrored},
            self.ocr.provenance(mirrored))

    def test_it_is_the_inverse_of_the_shell_rule(self):
        # The two halves live in different languages; this is the test that
        # fails if either changes alone.
        source = "/Volumes/BRICK/Images for Chris/CHIN1236.jpg"
        _, mirrored = mirror_path_for(source)
        os.environ["IMAGECAT_MIRROR_ROOT"] = "/srv/imagecat/data/staging/images"
        self.assertEqual(source, self.ocr.provenance(mirrored)["orig_path"])

    def test_a_file_outside_the_mirror_reports_nothing(self):
        # --no-mirror: the id is already the original, so there is no pair.
        self.assertEqual({}, self.ocr.provenance("/Volumes/BRICK/pics/a.jpg"))

    def test_a_prefix_that_is_not_a_directory_boundary_is_not_a_mirror(self):
        # /srv/imagecat/data/staging/images-old/... starts with the root as a
        # string and is not inside it.
        self.assertEqual(
            {}, self.ocr.provenance(
                "/srv/imagecat/data/staging/images-old/a.jpg"))

    def test_no_root_configured_reports_nothing(self):
        os.environ.pop("IMAGECAT_MIRROR_ROOT", None)
        home = os.environ.pop("IMAGECAT_HOME", None)
        oodt = os.environ.pop("OODT_HOME", None)
        try:
            self.assertEqual({}, self.ocr.provenance("/anything/a.jpg"))
        finally:
            if home:
                os.environ["IMAGECAT_HOME"] = home
            if oodt:
                os.environ["OODT_HOME"] = oodt

    def test_the_document_carries_it(self):
        text = body(OCR_PATH)
        self.assertIn("doc.update(provenance(path))", text)
        # After the id is set, so a doc without provenance still has an id.
        self.assertLess(text.index('"id": path'),
                        text.index("doc.update(provenance(path))"))


class MirroringIsTheDefault(unittest.TestCase):
    def setUp(self):
        self.text = body()
        self.index = extract("cmd_index")

    def test_it_mirrors_unless_told_not_to(self):
        self.assertRegex(self.index, r"local mirror=true")

    def test_no_mirror_turns_it_off(self):
        self.assertRegex(self.index, r"--no-mirror\)\s*mirror=false")

    def test_the_catalogued_tree_is_the_mirrored_one(self):
        # The id is whatever find lists, so this is the line that decides
        # what every document is called.
        self.assertRegex(self.index, r'find "\$listed" -type f')
        self.assertIn('listed="$dest"', self.index)
        self.assertIn('listed="$src"', self.index)

    def test_appledouble_sidecars_are_neither_copied_nor_listed(self):
        self.assertIn("--exclude='._*'", self.index)
        self.assertIn("! -name '._*'", self.index)

    def test_a_failed_mirror_stops_the_run(self):
        # Indexing after a half-finished copy catalogues a partial corpus
        # and looks like a successful smaller one.
        self.assertIn("Mirroring failed", self.index)

    def test_help_documents_it(self):
        start = self.text.index("  index <dir> [dir...]")
        usage = self.text[start:self.text.index("  reset [", start)]
        self.assertIn("--no-mirror", usage)


class TheSchemaDeclaresThem(unittest.TestCase):
    def test_both_fields_are_declared_single_valued(self):
        import xml.etree.ElementTree as ET
        root = ET.parse(SCHEMA).getroot()
        found = {f.get("name"): f for f in root.iter("field")}
        for name in ("orig_path", "mirror_path"):
            self.assertIn(name, found)
            # The catch-all dynamicField is multiValued, which would turn an
            # exact path match into a list membership test.
            self.assertEqual("false", found[name].get("multiValued"))
            self.assertEqual("string", found[name].get("type"))


if __name__ == "__main__":
    unittest.main()
