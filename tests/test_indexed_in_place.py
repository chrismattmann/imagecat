"""Images are catalogued where they live, and duplicates do not pay twice.

The document id used to be the path of a copy ImageCat had made under
data/staging. So the catalogue could not answer the question it exists to
answer -- where did this picture come from -- and the corpus was stored
twice, 1.8G for 686 images and growing with the collection.

The sha1 was already being computed, just afterwards, where it recorded
what had been done rather than deciding what to do.

A local copy is made again, because ImageSpace reads the source on every
request and an external volume serves about 47 MB/s here against 3258 MB/s
locally. That is a different question from what an image is called, and
these tests are about what it is called: the id is the source path whether
or not a copy exists. The copy is a read cache, and the tests for it are in
tests/test_index_stages_by_default.py.
"""

import ast
import importlib.util
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGECAT = os.path.join(ROOT, "distribution", "src", "main", "resources",
                        "bin", "imagecat")
CRAWL = os.path.join(ROOT, "pge", "src", "main", "resources", "policy",
                     "PgeConfig_Crawl.xml")
OCR_PY = os.path.join(ROOT, "pge", "src", "main", "resources", "bin",
                      "imagecat-ocr", "imagecat-ocr.py")
IMAGES_PY = os.path.join(ROOT, "imagespace", "server", "images.py")


def body(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TheCatalogueSaysWhereAPictureCameFrom(unittest.TestCase):
    """What #84 established, and how it is kept now.

    #84 removed a copy because the id was the copy's path and the original
    was nowhere on the record. The copy is back, as the default, because
    ImageSpace reads the catalogued file on every first view and an external
    volume is 70x slower than local disk.

    What makes that safe is not avoiding the copy. It is that the mirror path
    is a pure function of the source -- so the same image always takes the
    same id -- and that the original is written down rather than inferred.
    The old scheme had neither: staging_dest chose names by what had been
    staged before, and nothing recorded the source but a marker file.

    This class used to assert the script contained no "rsync", which is a
    mechanism rather than a property, and it failed on a change it was not
    written to catch.
    """

    def test_the_original_is_recorded_on_the_document(self):
        self.assertIn("doc.update(provenance(path))", body(OCR_PY))

    def test_the_old_naming_scheme_is_still_gone(self):
        # staging_dest picked a destination, and a .imagecat-source marker
        # remembered which source it held, because the name did not say.
        text = body(IMAGECAT)
        self.assertNotIn("staging_dest", text)
        self.assertNotRegex(text, r'>\s*"?\$\{?dest\}?/\.imagecat-source')

    def test_the_mirror_is_derived_not_remembered(self):
        # One expression, no state: the reason an id built from it is stable.
        self.assertRegex(body(IMAGECAT),
                         r'mirror_path_for\(\) \{\s*\n\s*printf')


class ADuplicateDoesNotPayForOcrTwice(unittest.TestCase):
    def setUp(self):
        self.text = body(OCR_PY)

    def test_the_hash_is_taken_before_ocr_not_after(self):
        hashed = self.text.index("shas = [sha1_of(path) for path in paths]")
        loaded = self.text.index("ocr, hf_id = load_ocr(")
        self.assertLess(hashed, loaded,
                        "the hash must be known before any OCR is done")

    def test_known_text_is_reused(self):
        self.assertIn("ocr_by_sha1", self.text)
        self.assertIn("reused += 1", self.text)

    def test_a_duplicate_still_gets_its_own_document(self):
        # Dedup skips the work, not the document. Two paths with identical
        # bytes are two facts about where that image lives; dropping one
        # would lose exactly the provenance indexing in place was for.
        self.assertIn('"id": path', self.text)

    def test_dedup_can_be_turned_off(self):
        self.assertIn("--no-dedup", self.text)

    def test_a_lookup_failure_does_not_stop_the_chunk(self):
        self.assertIn("will OCR everything", self.text)

    def test_it_still_parses(self):
        ast.parse(self.text, filename=OCR_PY)


class TheSeparateSha1PassIsGone(unittest.TestCase):
    def test_the_crawl_pge_no_longer_runs_it(self):
        self.assertNotIn("sha1sum.py", body(CRAWL))

    def test_the_script_is_deleted(self):
        path = os.path.join(ROOT, "pge", "src", "main", "resources", "bin",
                            "sha1sum")
        self.assertFalse(os.path.exists(path),
                         "it queried for documents without sha1sum_s_md, and "
                         "imagecat-ocr.py sets that field on every document "
                         "it posts, so it matched nothing")


class AnUnreachableSourceStillShowsThumbnails(unittest.TestCase):
    def setUp(self):
        self.text = body(IMAGES_PY)

    def test_a_thumbnail_does_not_require_the_source(self):
        # Images live on whatever volume holds them, which may not be mounted.
        # A grid of thumbnails already on disk is exactly what should still
        # work then; checking the source first emptied the whole browser.
        self.assertIn("must_exist=False", self.text)

    def test_a_missing_source_is_503_not_404(self):
        # 404 says "no such image". The image exists and is catalogued; the
        # host just cannot reach it.
        self.assertIn("status_code=503", self.text)

    def test_a_full_size_original_still_requires_the_source(self):
        # There is nothing to serve it from if the source is away.
        full = self.text.index("if not width:")
        thumb = self.text.index("must_exist=False")
        self.assertLess(full, thumb)

    def test_it_still_parses(self):
        ast.parse(self.text, filename=IMAGES_PY)


class AppleDoubleSidecarsAreNotImages(unittest.TestCase):
    """A ._NAME.jpg is a resource fork, not a picture.

    A volume mounted over AFP or SMB carries one beside every file, and
    "._CHIN9997.jpg" matches *.jpg as readily as the image does. BigTranslate
    ingested 2,806 of them as corpus before anyone noticed the file count was
    exactly double.
    """

    def test_the_walk_excludes_them(self):
        text = body(IMAGECAT)
        for line in text.splitlines():
            if "-iname '*.jpg'" in line and "find" in line:
                self.assertIn("! -name '._*'", line,
                              "this find would take sidecars for images: %s"
                              % line.strip())

    def test_find_actually_behaves_that_way(self):
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "real.jpg"), "w").close()
            open(os.path.join(tmp, "._real.jpg"), "w").close()
            out = subprocess.run(
                ["find", tmp, "-type", "f", "!", "-name", "._*",
                 "(", "-iname", "*.jpg", "-o", "-iname", "*.jpeg", ")"],
                capture_output=True, text=True).stdout.split()
            names = sorted(os.path.basename(x) for x in out)
            self.assertEqual(names, ["real.jpg"])


if __name__ == "__main__":
    unittest.main()
