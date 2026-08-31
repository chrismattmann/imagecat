import unittest

from server.solr import field_query, filter_queries, is_field_query, parse_field_clause, search_params, user_query


class QueryTests(unittest.TestCase):
    def test_star_is_match_all(self):
        self.assertEqual(user_query("*"), "*:*")
        self.assertEqual(user_query("  "), "*:*")
        self.assertEqual(user_query(None), "*:*")

    def test_text_passes_through(self):
        self.assertEqual(user_query("Elisa"), "Elisa")

    def test_field_query_quotes_and_escapes(self):
        self.assertEqual(field_query("tiff_Make", "Canon"), 'tiff_Make:"Canon"')
        self.assertEqual(field_query("By_line", 'Elisa "X"'), 'By_line:"Elisa \\"X\\""')
        self.assertTrue(is_field_query('tiff_Make:"Canon"'))
        self.assertFalse(is_field_query("Elisa"))
        with self.assertRaises(ValueError):
            field_query("clip_score", "0.9")
        with self.assertRaises(ValueError):
            field_query("tiff_Make", "")

    def test_parse_field_clause_roundtrip(self):
        self.assertEqual(parse_field_clause('tiff_Make:"Canon"'), ("tiff_Make", "Canon"))
        self.assertEqual(
            parse_field_clause(field_query("By_line", 'Elisa "X"')),
            ("By_line", 'Elisa "X"'),
        )

    def test_filter_queries_and_search_params(self):
        clauses = filter_queries(
            ['Exif_IFD0_Artist:"Matteo Chinellato"', 'tiff_Make:"Canon"']
        )
        self.assertEqual(
            clauses,
            ['Exif_IFD0_Artist:"Matteo Chinellato"', 'tiff_Make:"Canon"'],
        )
        params = search_params("*", 0, 24, clauses)
        self.assertEqual(params["q"], "*:*")
        self.assertEqual(params["fq"], clauses)
        self.assertEqual(params["sort"], "id asc")
        mixed = search_params("Elisa", 0, 24, ['tiff_Make:"Canon"'])
        self.assertEqual(mixed["q"], "Elisa")
        self.assertEqual(mixed["defType"], "edismax")
        self.assertEqual(mixed["fq"], ['tiff_Make:"Canon"'])


if __name__ == "__main__":
    unittest.main()
