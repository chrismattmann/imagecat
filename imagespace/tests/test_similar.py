import tempfile
import unittest
from pathlib import Path

import numpy as np

from server.similar import ClipIndex, save_index


class SimilarTests(unittest.TestCase):
    def test_nearest_is_the_close_vector(self):
        ids = ["a.jpg", "b.jpg", "c.jpg"]
        vectors = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.95, 0.05, 0.0],
                [0.0, 1.0, 0.0],
            ],
            dtype="float32",
        )
        with tempfile.TemporaryDirectory() as tmp:
            save_index(ids, vectors, {"model": "test", "dim": 3}, tmp)
            index = ClipIndex(tmp)
            self.assertTrue(index.available())
            hits = index.similar("a.jpg", n=2)
            self.assertEqual(hits[0]["id"], "b.jpg")
            self.assertGreater(hits[0]["clip_score"], hits[1]["clip_score"])
            self.assertNotIn("a.jpg", [h["id"] for h in hits])
            self.assertEqual(index.meta.get("backend"), "faiss")
            self.assertTrue((Path(tmp) / "index.faiss").is_file())

    def test_missing_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = ClipIndex(Path(tmp) / "nope")
            self.assertFalse(index.available())
            self.assertIsNone(index.similar("a.jpg"))


if __name__ == "__main__":
    unittest.main()
