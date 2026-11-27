"""Tests for manual_refresh. Run: python -m unittest test_manual_refresh -v"""
import json
import pathlib
import unittest

import manual_refresh as mr
from chunk_tree import VERSION, chunk_page

CORPUS = pathlib.Path(__file__).resolve().parent.parent / "laptop-scraper" / "corpus"


def stored(hash_="h1", chunks=100, version=VERSION):
    return {'hash': hash_, 'chunker_version': version, 'chunks': chunks}


class DecideTest(unittest.TestCase):
    def test_unchanged(self):
        self.assertEqual(mr.decide({'hash': 'h1', 'chunks': 100}, stored())[0], 'unchanged')

    def test_changed_hash_updates(self):
        self.assertEqual(mr.decide({'hash': 'h2', 'chunks': 105}, stored())[0], 'update')

    def test_not_indexed_updates(self):
        self.assertEqual(mr.decide({'hash': 'h1', 'chunks': 100}, stored(None, 0))[0], 'update')

    def test_new_chunker_version_updates_even_if_text_is_the_same(self):
        action, reason = mr.decide({'hash': 'h1', 'chunks': 100}, stored(version='1.0.0'))
        self.assertEqual(action, 'update')
        self.assertIn('chunker', reason)

    def test_much_smaller_scrape_is_suspicious_unless_forced(self):
        self.assertEqual(mr.decide({'hash': 'h2', 'chunks': 10}, stored())[0], 'suspicious')
        self.assertEqual(mr.decide({'hash': 'h2', 'chunks': 10}, stored(), force=True)[0], 'update')

    def test_force_reindexes_unchanged(self):
        self.assertEqual(mr.decide({'hash': 'h1', 'chunks': 100}, stored(), force=True)[0], 'update')


class RefreshFamilyTest(unittest.TestCase):
    source = {'family': '9242-01', 'name': 'IBM Power S1112', 'url': 'https://www.ibm.com/docs/en/announcements/x'}

    def setUp(self):
        self.calls = []
        self.html = '<html/>'
        self._build = mr.build_chunks
        mr.build_chunks = lambda html, source: ({'published': '1 Jan'}, [
            {'metadata': {'content_hash': 'new'}} for _ in range(100)])

    def tearDown(self):
        mr.build_chunks = self._build

    def run_it(self, stored_state, fetch=None, force=False):
        def index(source, page, chunks):
            self.calls.append(source['family'])
            return len(chunks), 0
        return mr.refresh_family(self.source, 'http://scraper', lambda fam: stored_state, index, force,
                                 fetch=fetch or (lambda base, url: self.html))

    def test_changed_family_is_indexed(self):
        res = self.run_it(stored('old', 100))
        self.assertEqual((res['status'], res['indexed'], self.calls), ('updated', 100, ['9242-01']))

    def test_unchanged_family_is_not_indexed(self):
        res = self.run_it(stored('new', 100))
        self.assertEqual((res['status'], self.calls), ('unchanged', []))

    def test_suspicious_family_keeps_the_old_index(self):
        res = self.run_it(stored('old', 1000))
        self.assertEqual((res['status'], self.calls), ('suspicious', []))

    def test_scrape_failure_is_reported_not_raised(self):
        def boom(base, url):
            raise RuntimeError('403')
        res = self.run_it(stored('old', 100), fetch=boom)
        self.assertEqual((res['status'], self.calls), ('failed', []))
        self.assertIn('403', res['reason'])


class RealCorpusTest(unittest.TestCase):
    def test_hash_is_stable_across_chunking_runs(self):
        files = sorted(CORPUS.glob("*.json"))
        if not files:
            self.skipTest("no corpus")
        page = json.loads(files[0].read_text(encoding="utf-8"))
        a, _ = chunk_page(page)
        b, _ = chunk_page(page)
        self.assertEqual(a[0]['metadata']['content_hash'], b[0]['metadata']['content_hash'])
        self.assertNotEqual(a[0]['metadata']['ingestion_timestamp'], '')


if __name__ == "__main__":
    unittest.main()
