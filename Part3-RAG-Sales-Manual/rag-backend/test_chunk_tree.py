"""Tests for chunk_tree.split_text. Run: python -m unittest test_chunk_tree -v"""
import unittest

import chunk_tree as ct

AIX = ("If installing the AIX operating system LPAR with any I/O configuration (one of these):\n\n"
       + "\n".join(f"- AIX Version 7.{i} with the 7{i}00-0{i} Technology Level, or later" for i in range(1, 4)))
VIOS = ("If installing the AIX operating system Virtual I/O only LPAR (one of these):\n\n"
        + "\n".join(f"- AIX Version 6.{i} with the 6{i}00-0{i} Technology Level, or later" for i in range(1, 4)))


class LeadInTest(unittest.TestCase):
    def test_lead_in_stays_with_its_list(self):
        parts = ct.split_text(AIX + "\n\n" + VIOS, cap=len(AIX) + 20)  # room for only one list per chunk
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[0].startswith("If installing the AIX operating system LPAR with any I/O"))
        self.assertTrue(parts[1].startswith("If installing the AIX operating system Virtual I/O only"))
        self.assertIn("AIX Version 6.1", parts[1])

    def test_text_without_lead_ins_is_unchanged(self):
        self.assertEqual(ct.split_text("one\n\ntwo\n\nthree"), ["one\n\ntwo\n\nthree"])

    def test_lead_in_before_a_table_is_not_glued(self):
        blocks = ct._blocks("Models:\n\n| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertEqual(len(blocks), 2)


if __name__ == "__main__":
    unittest.main()
