"""Daily check of the IBM Power Sales Manuals: fetch from the Code Engine scraper, compare a content hash,
and re-index only the families that changed.

The scraper (Code Engine, headless Chrome) returns the rendered page HTML. It is parsed and chunked with
the same code as the first load (`ibm_docs_tree.parse_page`, `chunk_tree.chunk_page`), so the content hash of
a family is identical whichever machine scraped it. The stored hash lives in the chunks' metadata.
"""
import logging
import time
from datetime import datetime

import requests

from chunk_tree import VERSION as CHUNKER_VERSION, chunk_page
from ibm_docs_tree import parse_page

logger = logging.getLogger(__name__)

# A new scrape with far fewer chunks than the stored one is more likely a broken page (consent banner, 403
# shell, half-rendered SPA) than a real rewrite. It is not indexed unless the caller forces it.
MIN_KEEP_RATIO = 0.5


def decide(new, stored, force=False):
    """('unchanged' | 'update' | 'suspicious', reason).

    new    = {'hash': str, 'chunks': int}
    stored = {'hash': str|None, 'chunker_version': str|None, 'chunks': int}  (chunks 0 = nothing indexed)
    """
    if stored['chunks'] == 0 or not stored['hash']:
        return 'update', 'not indexed yet'
    if force:
        return 'update', 'forced'
    if new['chunks'] < MIN_KEEP_RATIO * stored['chunks']:
        return 'suspicious', f"new scrape has {new['chunks']} chunks, stored index has {stored['chunks']}"
    if new['hash'] != stored['hash']:
        return 'update', 'content changed'
    if stored['chunker_version'] != CHUNKER_VERSION:
        return 'update', f"chunker {stored['chunker_version']} -> {CHUNKER_VERSION}"
    return 'unchanged', 'hash matches'


def fetch_html(scraper_url, url, attempts=3, timeout=300):
    """Rendered HTML of an IBM Docs page from the Code Engine scraper. Retries: the first call after idle
    pays a cold start of up to a minute."""
    last = None
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(f"{scraper_url.rstrip('/')}/scrape", params={'url': url, 'wait': 10}, timeout=timeout)
            data = r.json()
            if r.status_code == 200 and data.get('success') and data.get('html'):
                return data['html']
            last = data.get('error') or f"HTTP {r.status_code}"
        except (requests.exceptions.RequestException, ValueError) as e:
            last = str(e)
        logger.warning(f"[Refresh] scrape attempt {attempt}/{attempts} failed for {url}: {last}")
        if attempt < attempts:
            time.sleep(15)
    raise RuntimeError(f"scrape failed: {last}")


def build_chunks(html, source):
    page = parse_page(html)
    page.update(url=source['url'], scraped_at=datetime.now().isoformat())
    chunks, _ = chunk_page(page)
    return page, chunks


def refresh_family(source, scraper_url, get_stored, index_chunks, force=False, fetch=fetch_html):
    """Check one family. Returns a result dict with 'status' in unchanged / updated / suspicious / failed.

    get_stored(family)                            -> stored dict for `decide`
    index_chunks(source, page, chunks)            -> (indexed, failed); replaces the family's index
    """
    result = {'family': source['family'], 'name': source.get('name'), 'url': source['url']}
    try:
        page, chunks = build_chunks(fetch(scraper_url, source['url']), source)
        if not chunks:
            raise RuntimeError('page parsed to zero chunks')
        new = {'hash': chunks[0]['metadata']['content_hash'], 'chunks': len(chunks)}
        stored = get_stored(source['family'])
        action, reason = decide(new, stored, force)
        result.update(reason=reason, new_hash=new['hash'], old_hash=stored['hash'],
                      new_chunks=new['chunks'], old_chunks=stored['chunks'], published=page.get('published'))
        if action == 'update':
            indexed, failed = index_chunks(source, page, chunks)
            result.update(status='updated' if not failed else 'failed', indexed=indexed, failed=failed)
        else:
            result['status'] = action
    except Exception as e:  # one bad page must not stop the other 26
        logger.exception(f"[Refresh] {source['family']} failed")
        result.update(status='failed', reason=str(e))
    return result
