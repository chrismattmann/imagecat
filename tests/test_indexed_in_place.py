"""Images are catalogued where they live, and duplicates do not pay twice.

The document id used to be the path of a copy ImageCat had made under
data/staging. So the catalogue could not answer the question it exists to
answer -- where did this picture come from -- and the corpus was stored
twice, 1.8G for 686 images and growing with the collection.

The sha1 was already being computed, just afterwards, where it recorded
what had been done rather than deciding what to do.
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


class NothingIsCopiedBeforeIndexing(unittest.TestCase):
    def test_the_indexer_does_not_rsync(self):
        self.assertNotIn("rsync", body(IMAGECAT),
                         "the corpus is being copied before it is indexed")

    def test_there_is_no_staging_destination_left(self):
        self.assertNotIn("staging_dest", body(IMAGECAT))

    def test_the_file_list_holds_source_paths(self):
        # find runs over $src, the directory the user named, not over a copy.
        text = body(IMAGECAT)
        self.assertRegex(text, r'find "\$src" -type f')
        self.assertNotRegex(text, r'find "\$dest" -type f')


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


if __name__ == "__main__":
    unittest.main()
