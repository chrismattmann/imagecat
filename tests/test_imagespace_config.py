"""ImageSpace data paths follow OODT_HOME when installed in ImageCat."""

import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IS = os.path.join(ROOT, "imagespace")


class DataRootTests(unittest.TestCase):
    def setUp(self):
        import sys
        from importlib import reload
        if IS not in sys.path:
            sys.path.insert(0, IS)
        for key in ("IMAGE_SPACE_DATA", "OODT_HOME", "IMAGECAT_HOME", "IMAGE_SPACE_INDEX_DIR"):
            os.environ.pop(key, None)
        from server import config
        reload(config)
        self.config = config

    def test_standalone_defaults_to_data(self):
        self.assertEqual(self.config.data_root(), "data")
        self.assertEqual(self.config.index_dir(), os.path.join("data", "clip"))

    def test_oodt_home_uses_data_imagespace(self):
        from importlib import reload
        os.environ["OODT_HOME"] = "/opt/imagecat"
        reload(self.config)
        self.assertEqual(self.config.data_root(), "/opt/imagecat/data/imagespace")
        self.assertEqual(self.config.fg_dir(), "/opt/imagecat/data/imagespace/fg")
        self.assertEqual(self.config.thumb_dir(), "/opt/imagecat/data/imagespace/thumbs")
        self.assertEqual(self.config.meta_dir(), "/opt/imagecat/data/imagespace/meta")

    def test_explicit_data_wins(self):
        from importlib import reload
        os.environ["OODT_HOME"] = "/opt/imagecat"
        os.environ["IMAGE_SPACE_DATA"] = "/tmp/is"
        reload(self.config)
        self.assertEqual(self.config.data_root(), "/tmp/is")
        self.assertEqual(self.config.index_dir(), os.path.join("/tmp/is", "clip"))


    def test_query_helpers_still_import(self):
        from server.solr import user_query
        self.assertEqual(user_query("*"), "*:*")


if __name__ == "__main__":
    unittest.main()
