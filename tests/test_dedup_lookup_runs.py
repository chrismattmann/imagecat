"""The dedup lookup, executed rather than read.

#84 added ocr_by_sha1 and tested it by asserting the source contained the
string "ocr_by_sha1". It did. It also called pysolr without importing it,
so the first real chunk died with

    NameError: name 'pysolr' is not defined

after loading the OCR model and reading all 686 paths. A test that greps
for a name cannot catch that; only calling the function can.

pysolr is imported inside the functions that use it, so the module can be
read without it installed. These tests supply a fake one and exercise the
lookup for real.
"""

import importlib.util
import os
import sys
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PGE_BIN = os.path.join(ROOT, "pge", "src", "main", "resources", "bin")
OCR_PATH = os.path.join(PGE_BIN, "imagecat-ocr", "imagecat-ocr.py")


class _FakeSolr:
    """Records what it was asked, answers from a fixed set."""

    last_queries: list = []

    def __init__(self, url, **kw):
        self.url = url

    def search(self, query, **kw):
        _FakeSolr.last_queries.append(query)
        known = {
            "aaa": {"sha1sum_s_md": "aaa", "ocr_text": "from aaa",
                    "ocr_model_s": "model-1"},
            "ccc": {"sha1sum_s_md": ["ccc"], "ocr_text": "from ccc",
                    "ocr_model_s": ["model-2"]},
        }
        return [doc for sha, doc in known.items() if '"%s"' % sha in query]


class _Raises(_FakeSolr):
    def search(self, query, **kw):
        raise RuntimeError("solr is down")


def load_ocr_module(solr_class):
    fake = types.ModuleType("pysolr")
    fake.Solr = solr_class
    sys.modules["pysolr"] = fake
    if PGE_BIN not in sys.path:
        sys.path.insert(0, PGE_BIN)
    spec = importlib.util.spec_from_file_location("imagecat_ocr_under_test",
                                                  OCR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheLookupRuns(unittest.TestCase):
    def setUp(self):
        _FakeSolr.last_queries = []
        self.ocr = load_ocr_module(_FakeSolr)

    def test_no_hashes_asks_nothing(self):
        self.assertEqual(self.ocr.ocr_by_sha1("http://x/solr/c", []), {})
        self.assertEqual(_FakeSolr.last_queries, [])

    def test_a_known_hash_comes_back_with_its_text(self):
        got = self.ocr.ocr_by_sha1("http://x/solr/c", ["aaa", "bbb"])
        self.assertEqual(got["aaa"]["ocr_text"], "from aaa")
        self.assertNotIn("bbb", got)

    def test_a_multivalued_field_is_unwrapped(self):
        # Solr hands back a list for a multi-valued field; the key has to be
        # the string or nothing matches.
        got = self.ocr.ocr_by_sha1("http://x/solr/c", ["ccc"])
        self.assertIn("ccc", got)

    def test_empty_hashes_are_not_queried_for(self):
        self.ocr.ocr_by_sha1("http://x/solr/c", ["aaa", "", None])
        joined = " ".join(_FakeSolr.last_queries)
        self.assertNotIn('sha1sum_s_md:""', joined)

    def test_it_batches_rather_than_asking_once_per_hash(self):
        self.ocr.ocr_by_sha1("http://x/solr/c", ["h%d" % i for i in range(450)])
        # 450 hashes, 200 to a query
        self.assertEqual(len(_FakeSolr.last_queries), 3)


class AFailedLookupDoesNotStopTheChunk(unittest.TestCase):
    def test_it_returns_empty_so_everything_is_ocred(self):
        ocr = load_ocr_module(_Raises)
        self.assertEqual(ocr.ocr_by_sha1("http://x/solr/c", ["aaa"]), {})


if __name__ == "__main__":
    unittest.main()
