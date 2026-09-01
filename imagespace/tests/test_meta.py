import unittest

from server.meta import golden_score, jaccard, key_set, skip_field, value_set, MetaIndex


class MetaJaccardTests(unittest.TestCase):
    def test_skips_icc_and_system_fields(self):
        self.assertTrue(skip_field("id"))
        self.assertTrue(skip_field("ocr_text"))
        self.assertTrue(skip_field("jaccard_keys_f"))
        self.assertTrue(skip_field("ICC_Green_TRC"))
        self.assertTrue(skip_field("Padding"))
        self.assertFalse(skip_field("tiff_Make"))
        self.assertFalse(skip_field("content_type"))

    def test_key_set_drops_skipped(self):
        doc = {
            "id": "/a.jpg",
            "ocr_text": "hello",
            "tiff_Make": "Canon",
            "ICC_Green_TRC": "0.0",
        }
        self.assertEqual(key_set(doc), frozenset(["tiff_Make"]))

    def test_value_set_one_token_per_multivalue(self):
        doc = {"id": "/a.jpg", "tiff_Make": ["Canon", "Canon"], "Software": "GIMP"}
        tokens = value_set(doc)
        self.assertIn("tiff_Make=Canon", tokens)
        self.assertIn("Software=GIMP", tokens)
        self.assertEqual(len([t for t in tokens if t.startswith("tiff_Make=")]), 1)

    def test_golden_key_score_is_share_of_union(self):
        # ETLlib compareKeySimilarity: |keys| / |union|
        a = frozenset(["tiff_Make", "tiff_Model"])
        b = frozenset(["tiff_Make"])
        union = a | b
        self.assertAlmostEqual(golden_score(a, union), 1.0)
        self.assertAlmostEqual(golden_score(b, union), 0.5)
        self.assertAlmostEqual(golden_score(frozenset(), union), 0.0)

    def test_pairwise_keys_vs_values(self):
        phone = {
            "id": "phone.jpg",
            "tiff_Make": "Apple",
            "tiff_Model": "iPhone",
            "Software": "Photos",
        }
        same_cam = {
            "id": "same-cam.jpg",
            "tiff_Make": "Apple",
            "tiff_Model": "iPhone",
            "Software": "Lightroom",
        }
        stripped = {"id": "stripped.jpg", "ocr_text": "no exif"}
        index = MetaIndex()
        index.load_docs([phone, same_cam, stripped])
        key_hits = index.similar("phone.jpg", n=2, space="keys")
        self.assertEqual(key_hits[0]["id"], "same-cam.jpg")
        self.assertGreater(key_hits[0]["meta_score"], key_hits[1]["meta_score"])
        val_hits = index.similar("phone.jpg", n=2, space="vals")
        self.assertEqual(val_hits[0]["id"], "same-cam.jpg")
        # Same keys, different Software → keys Jaccard is 1, values is not.
        self.assertEqual(jaccard(key_set(phone), key_set(same_cam)), 1.0)
        self.assertLess(jaccard(value_set(phone), value_set(same_cam)), 1.0)

    def test_two_stripped_files_are_neighbors(self):
        a = {"id": "a.jpg", "ocr_text": "x"}
        b = {"id": "b.jpg", "ocr_text": "y"}
        c = {"id": "c.jpg", "tiff_Make": "Canon"}
        index = MetaIndex()
        index.load_docs([a, b, c])
        hits = index.similar("a.jpg", n=2, space="keys")
        self.assertEqual(hits[0]["id"], "b.jpg")
        self.assertEqual(hits[0]["meta_score"], 1.0)

    def test_atomic_xml_uses_update_set(self):
        from server.meta import _atomic_xml

        xml = _atomic_xml(
            [{"id": "/a & b.jpg", "jaccard_keys_f": 0.5, "jaccard_vals_f": 0.25}]
        ).decode()
        self.assertIn('update="set"', xml)
        self.assertIn("/a &amp; b.jpg", xml)
        self.assertNotIn('{"set"', xml)

    def test_solr_scores_match_golden_union(self):
        docs = [
            {"id": "rich.jpg", "tiff_Make": "Apple", "tiff_Model": "iPhone"},
            {"id": "poor.jpg", "tiff_Make": "Apple"},
        ]
        index = MetaIndex()
        index.load_docs(docs)
        by_id = {row["id"]: row for row in index.solr_scores()}
        self.assertAlmostEqual(by_id["rich.jpg"]["jaccard_keys_f"], 1.0)
        self.assertAlmostEqual(by_id["poor.jpg"]["jaccard_keys_f"], 0.5)


if __name__ == "__main__":
    unittest.main()
