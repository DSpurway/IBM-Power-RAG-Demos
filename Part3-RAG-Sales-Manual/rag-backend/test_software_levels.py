"""Tests for software_levels. Run: python -m unittest test_software_levels -v"""
import unittest

from software_levels import MINIMUM_WORDS, oldest_levels

E980 = """Technical description > Software requirements

If installing the AIX operating system LPAR with any I/O configuration (one of these):
- AIX Version 7.3 with the 7300-00 Technology Level, or later
- AIX 7.2 with the 7200-04 Technology Level, or later
- AIX Version 7.1 with the 7100-05 Technology Level and Service Pack 7100-05-03-1838 or later
- AIX Version 6.1 with the 6100-09 Technology Level and Service Pack 6100-09-12-1838 or later (AIX 6.1 service extension required)
- AIX Version 7.2 with the 7200-01 Technology Level and Service Pack 7200-01-05-1845 or later

If installing the AIX operating system Virtual I/O only LPAR (one of these):
- AIX Version 7.3 with the 7300-00 Technology Level, or later
- AIX Version 7.2 with the 7200-00 Technology Level and Service Pack 7200-00-02-1614, or later
- AIX Version 7.1 with the 7100-04 Technology Level and Service Pack 7100-04-02-1614, or later"""

IBM_I = """Technical description > Software requirements

If installing the IBM i operating system (one of these):
- IBM i 7.5, or later
- IBM i 7.3 TR5, or later
- IBM i 7.1 TR11, or later with latest PTFs
- IBM i 7.2 TR9, or later"""


class OldestLevelsTest(unittest.TestCase):
    def test_oldest_aix_per_list(self):
        got = oldest_levels([E980], ['aix'])
        self.assertEqual(len(got), 2)
        self.assertTrue(got[0].startswith("AIX operating system LPAR with any I/O configuration: AIX Version 6.1 with the 6100-09"))
        self.assertIn("service extension required", got[0])
        self.assertTrue(got[1].startswith("AIX operating system Virtual I/O only LPAR: AIX Version 7.1 with the 7100-04"))

    def test_oldest_ibm_i(self):
        self.assertEqual(oldest_levels([IBM_I], ['ibm i']),
                         ["IBM i operating system: IBM i 7.1 TR11, or later with latest PTFs"])

    def test_other_operating_systems_and_missing_lists_give_nothing(self):
        self.assertEqual(oldest_levels([E980], ['linux']), [])
        self.assertEqual(oldest_levels(["no lists here"], ['aix']), [])
        self.assertEqual(oldest_levels([E980], []), [])

    def test_minimum_wording(self):
        for q in ("What is the minimum level of AIX?", "oldest IBM i release for the S1022", "AIX level of at least 7.2"):
            self.assertTrue(MINIMUM_WORDS.search(q), q)
        self.assertFalse(MINIMUM_WORDS.search("What level of AIX is needed to support the E980?"))


if __name__ == "__main__":
    unittest.main()
