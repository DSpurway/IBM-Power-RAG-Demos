"""Tests for server_mtm_mapper (reads sources.json). Run: python -m unittest test_server_mtm_mapper -v"""
import json
import unittest

import server_mtm_mapper as m


class MapperTest(unittest.TestCase):
    def test_every_source_is_mapped(self):
        with open(m.SOURCES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        sources = [s for st in data["sets"] for s in st["sources"]]
        self.assertGreaterEqual(len(sources), 27)
        for s in sources:
            for mtm in s["mtms"]:
                self.assertEqual(m.MTM_FAMILY_MAP[mtm], s["family"])
                self.assertEqual(
                    m.get_collection_name_for_mtm(mtm),
                    f"rag_family_{s['family'].replace('-', '_')}",
                )

    def test_model_names(self):
        self.assertEqual(m.get_mtm_for_model("S924"), "9009-42A")
        self.assertEqual(m.get_mtm_for_model("S924-G"), "9009-42G")
        self.assertEqual(m.get_mtm_for_model("IBM Power E980"), "9080-M9S")
        self.assertEqual(m.get_mtm_for_model("LC922"), "9006-22P")
        self.assertIsNone(m.get_mtm_for_model("NOSUCH"))

    def test_s1112_is_9242_not_9028(self):
        """S1112 = family 9242-01, MTMs 9242-21B (rack) and 9242-21T (tower). 9028-21B is the S1012."""
        self.assertEqual(m.MTM_SERVER_MAP["9242-21B"], "S1112")
        self.assertEqual(m.MTM_SERVER_MAP["9242-21T"], "S1112")
        self.assertEqual(m.MTM_SERVER_MAP["9028-21B"], "S1012")
        self.assertNotIn("9028-21N", m.MTM_SERVER_MAP)
        # both MTMs share one collection
        self.assertEqual(
            m.get_collection_name_for_mtm("9242-21B"),
            m.get_collection_name_for_mtm("9242-21T"),
        )
        self.assertEqual(m.get_collection_name_for_model("S1112"), "rag_family_9242_01")

    def test_unknown_mtm_falls_back_to_legacy_name(self):
        self.assertEqual(m.get_collection_name_for_mtm("1234-ABC"), "rag_mtm_1234_abc")


if __name__ == "__main__":
    unittest.main()
