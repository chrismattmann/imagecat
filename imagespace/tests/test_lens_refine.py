import os
import tempfile
import unittest

import numpy as np

from server.lens import apply_lens, keras_available, list_lenses, refine, save_lens, slugify
from server.similar import ClipIndex, save_index


@unittest.skipUnless(keras_available(), "Keras not installed")
class LensRefineTests(unittest.TestCase):
    def test_positives_rank_above_negatives(self):
        ids = ["pos.jpg", "neg.jpg", "other.jpg"]
        vectors = np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.8, 0.2, 0.0, 0.0],
            ],
            dtype="float32",
        )
        with tempfile.TemporaryDirectory() as tmp:
            save_index(ids, vectors, {"model": "test", "dim": 4}, tmp)
            index = ClipIndex(tmp)
            hits, stats = refine(index, ["pos.jpg"], ["neg.jpg"], n=3)
            ranked = [h["id"] for h in hits]
            self.assertEqual(stats["positive"], 1)
            self.assertEqual(stats["negative"], 1)
            self.assertLess(ranked.index("pos.jpg"), ranked.index("neg.jpg"))
            self.assertLess(ranked.index("other.jpg"), ranked.index("neg.jpg"))

    def test_needs_both_classes(self):
        ids = ["a.jpg", "b.jpg"]
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
        with tempfile.TemporaryDirectory() as tmp:
            save_index(ids, vectors, {"model": "test", "dim": 2}, tmp)
            index = ClipIndex(tmp)
            with self.assertRaises(ValueError):
                refine(index, ["a.jpg"], [], n=2)
            with self.assertRaises(ValueError):
                refine(index, ["missing.jpg"], ["also-missing.jpg"], n=2)

    def test_scores_are_descending_probabilities(self):
        ids = ["pos.jpg", "neg.jpg", "other.jpg"]
        vectors = np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.8, 0.2, 0.0, 0.0],
            ],
            dtype="float32",
        )
        with tempfile.TemporaryDirectory() as tmp:
            save_index(ids, vectors, {"model": "test", "dim": 4}, tmp)
            index = ClipIndex(tmp)
            hits, _stats = refine(index, ["pos.jpg"], ["neg.jpg"], n=3)
            scores = [h["lens_score"] for h in hits]
            self.assertEqual(scores, sorted(scores, reverse=True))
            for score in scores:
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)

    def test_save_list_apply(self):
        ids = ["pos.jpg", "neg.jpg", "other.jpg"]
        vectors = np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.8, 0.2, 0.0, 0.0],
            ],
            dtype="float32",
        )
        with tempfile.TemporaryDirectory() as tmp:
            save_index(ids, vectors, {"model": "test-clip", "dim": 4}, tmp)
            index = ClipIndex(tmp)
            os.environ["IMAGE_SPACE_LENSES_DIR"] = os.path.join(tmp, "lenses")
            try:
                meta = save_lens(index, "Same flyer", ["pos.jpg"], ["neg.jpg"])
                self.assertEqual(meta["slug"], "same-flyer")
                self.assertEqual(meta["clip_model"], "test-clip")
                listed = list_lenses()
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["slug"], "same-flyer")
                hits, stats = apply_lens(index, "same-flyer", n=3)
                ranked = [h["id"] for h in hits]
                self.assertEqual(stats["positive"], ["pos.jpg"])
                self.assertLess(ranked.index("pos.jpg"), ranked.index("neg.jpg"))
            finally:
                os.environ.pop("IMAGE_SPACE_LENSES_DIR", None)


class LensSlugTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Same flyer"), "same-flyer")
        self.assertEqual(slugify("  Weapons Faces  "), "weapons-faces")
        with self.assertRaises(ValueError):
            slugify("???")


if __name__ == "__main__":
    unittest.main()
