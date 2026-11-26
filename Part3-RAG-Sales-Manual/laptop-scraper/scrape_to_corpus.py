"""
Laptop (x86) scraper for IBM Sales Manual pages -> local corpus.

For each URL writes, into ./corpus/:
  <mtm>.html.gz   the fully rendered page (so we can re-parse/re-chunk without hitting IBM again)
  <mtm>.json      clean section tree (see ibm_docs_tree.py) + page_title, mtm, published, url, scraped_at

IBM's Akamai edge returns 403 to the default HeadlessChrome user-agent, so a normal Chrome UA is required.
Never calls IBM's /docs/api (disallowed by robots.txt); it only loads the page as a browser does.

Usage:  python scrape_to_corpus.py <url> [<url> ...]
        python scrape_to_corpus.py --reparse <mtm>      # rebuild <mtm>.json from the saved HTML
"""
import gzip
import json
import pathlib
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ibm_docs_tree import parse_page

HERE = pathlib.Path(__file__).resolve().parent
CORPUS = HERE / "corpus"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def fetch_html(url: str) -> str:
    o = Options()
    o.add_argument("--headless=new")
    o.add_argument("--window-size=1400,1000")
    o.add_argument("--disable-gpu")
    o.add_argument(f"--user-agent={UA}")
    d = webdriver.Chrome(options=o)
    d.set_page_load_timeout(90)
    try:
        d.get(url)
        try:
            WebDriverWait(d, 15).until(EC.element_to_be_clickable((By.ID, "truste-consent-button"))).click()
        except Exception:
            pass  # no cookie banner
        WebDriverWait(d, 120).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ibmdocs-content-container article.topic")))
        time.sleep(5)  # let lazy sections finish
        return d.page_source
    finally:
        d.quit()


def save(url: str, html: str):
    page = parse_page(html)
    name = (page["family"] or page["mtm"] or url.rstrip("/").split("/")[-1]).lower()
    CORPUS.mkdir(exist_ok=True)
    with gzip.open(CORPUS / f"{name}.html.gz", "wt", encoding="utf-8") as f:
        f.write(html)
    page.update(url=url, scraped_at=datetime.now().isoformat())
    (CORPUS / f"{name}.json").write_text(json.dumps(page, ensure_ascii=False, indent=1), encoding="utf-8")
    top = [(n["title"], len(n["text"]) + sum(len(c["text"]) for c in n["children"])) for n in page["tree"]]
    print(f"OK {name}: published={page['published']} sections={top}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--reparse":
        name = sys.argv[2].lower()
        with gzip.open(CORPUS / f"{name}.html.gz", "rt", encoding="utf-8") as f:
            old = json.loads((CORPUS / f"{name}.json").read_text(encoding="utf-8"))
            save(old["url"], f.read())
    else:
        for u in sys.argv[1:]:
            save(u, fetch_html(u))
