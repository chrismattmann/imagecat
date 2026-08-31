import tempfile
import unittest
from pathlib import Path

from PIL import Image

from server.images import make_thumb


class ThumbTests(unittest.TestCase):
    def test_thumb_is_smaller_jpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "big.jpg"
            dest = Path(tmp) / "thumb.jpg"
            Image.new("RGB", (2000, 1000), color=(40, 80, 120)).save(src, quality=95)
            make_thumb(src, dest, 360)
            self.assertTrue(dest.is_file())
            with Image.open(dest) as out:
                self.assertEqual(out.size[0], 360)
                self.assertLess(out.size[1], 360)
            self.assertLess(dest.stat().st_size, src.stat().st_size)


if __name__ == "__main__":
    unittest.main()
