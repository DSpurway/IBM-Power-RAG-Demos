"""
Scrape all 27 IBM Power Sales Manual pages to the local corpus on the x86 laptop.

Features:
- Single reusable Selenium WebDriver session with spoofed Chrome UA.
- Skips already-scraped servers unless --force is given.
- Saves <family/mtm>.html.gz and <family/mtm>.json into corpus/.
"""
import argparse
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

SERVERS = [
    # POWER11
    {"name": "IBM Power E1180", "mtm": "9080-HEU", "url": "https://www.ibm.com/docs/en/announcements/family-908005-power-e1180-enterprise-server-9080-heu"},
    {"name": "IBM Power E1150", "mtm": "9043-MRU", "url": "https://www.ibm.com/docs/en/announcements/family-904302-power-e1150-enterprise-midrange-technology-based-server-9043-mru"},
    {"name": "IBM Power S1124", "mtm": "9824-42A", "url": "https://www.ibm.com/docs/en/announcements/family-982402-power-s1124-9824-42a"},
    {"name": "IBM Power S1122", "mtm": "9824-22A", "url": "https://www.ibm.com/docs/en/announcements/family-982401-power-s1122-9824-22a"},
    {"name": "IBM Power S1112", "mtm": "9242-21B", "url": "https://www.ibm.com/docs/en/announcements/family-9242-01-power-s1112"},
    # POWER10
    {"name": "IBM Power E1080", "mtm": "9080-HEX", "url": "https://www.ibm.com/docs/en/announcements/power-e1080-enterprise-server"},
    {"name": "IBM Power E1050", "mtm": "9043-MRX", "url": "https://www.ibm.com/docs/en/announcements/power-e1050-enterprise-midrange-technology-based-server"},
    {"name": "IBM Power S1024", "mtm": "9105-42A", "url": "https://www.ibm.com/docs/en/announcements/power-s1024-9105-42a"},
    {"name": "IBM Power S1022", "mtm": "9105-22A", "url": "https://www.ibm.com/docs/en/announcements/power-s1022-9105-22a"},
    {"name": "IBM Power S1014", "mtm": "9105-41B", "url": "https://www.ibm.com/docs/en/announcements/power-s1014-9105-41b"},
    {"name": "IBM Power S1012", "mtm": "9028-21B", "url": "https://www.ibm.com/docs/en/announcements/family-9028-01-power-s1012"},
    {"name": "IBM Power L1024", "mtm": "9786-42H", "url": "https://www.ibm.com/docs/en/announcements/power-l1024-9786-42h"},
    {"name": "IBM Power L1022", "mtm": "9786-22H", "url": "https://www.ibm.com/docs/en/announcements/power-l1022-9786-22h"},
    # POWER9
    {"name": "IBM Power System E980", "mtm": "9080-M9S", "url": "https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s"},
    {"name": "IBM Power System E950", "mtm": "9040-MR9", "url": "https://www.ibm.com/docs/en/announcements/power-system-e950-9040-mr9"},
    {"name": "IBM Power System S924", "mtm": "9009-42A", "url": "https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42a"},
    {"name": "IBM Power System S924-G", "mtm": "9009-42G", "url": "https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42g"},
    {"name": "IBM Power System S922", "mtm": "9009-22A", "url": "https://www.ibm.com/docs/en/announcements/power-system-s922-9009-22a"},
    {"name": "IBM Power System S922-G", "mtm": "9009-22G", "url": "https://www.ibm.com/docs/en/announcements/power-system-s922-9009-22g"},
    {"name": "IBM Power System S914", "mtm": "9009-41A", "url": "https://www.ibm.com/docs/en/announcements/power-system-s914-9009-41a"},
    {"name": "IBM Power System S914-G", "mtm": "9009-41G", "url": "https://www.ibm.com/docs/en/announcements/power-system-s914-9009-41g-2023-10-24"},
    {"name": "IBM Power System H924", "mtm": "9223-42S", "url": "https://www.ibm.com/docs/en/announcements/power-system-h924-9223-42s-2023-10-24"},
    {"name": "IBM Power System H922", "mtm": "9223-22S", "url": "https://www.ibm.com/docs/en/announcements/power-system-h922-9223-22s-2023-10-24"},
    {"name": "IBM Power System IC922", "mtm": "9183-22X", "url": "https://www.ibm.com/docs/en/announcements/power-system-ic922-9183-22x-2021-12-14"},
    {"name": "IBM Power System L922", "mtm": "9008-22L", "url": "https://www.ibm.com/docs/en/announcements/power-system-l922-9008-22l"},
    {"name": "IBM Power System LC922", "mtm": "9006-22P", "url": "https://www.ibm.com/docs/en/announcements/power-system-lc922-9006-22p"},
    {"name": "IBM Power System LC921", "mtm": "9006-12P", "url": "https://www.ibm.com/docs/en/announcements/power-systems-lc921-9006-12p"},
]


def create_driver():
    o = Options()
    o.add_argument("--headless=new")
    o.add_argument("--window-size=1400,1000")
    o.add_argument("--disable-gpu")
    o.add_argument(f"--user-agent={UA}")
    d = webdriver.Chrome(options=o)
    d.set_page_load_timeout(90)
    return d


def scrape_server(driver, server_info: dict, force: bool = False):
    url = server_info["url"]
    name_hint = server_info["name"]
    CORPUS.mkdir(exist_ok=True)
    
    # Check if already scraped
    url_slug = url.rstrip("/").split("/")[-1].lower()
    possible_keys = [url_slug, server_info.get("mtm", "").lower()]
    if not force:
        for k in possible_keys:
            if k and (CORPUS / f"{k}.json").exists() and (CORPUS / f"{k}.html.gz").exists():
                print(f"     [SKIPPED] {name_hint} already exists as corpus/{k}.json (use --force to re-scrape)")
                return k
    
    print(f"\n---> Fetching {name_hint} ({url})...")
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "truste-consent-button"))).click()
        print("     [Clicked consent button]")
    except Exception:
        pass
    
    WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.ibmdocs-content-container article.topic")))
    time.sleep(3)  # brief settle time
    
    html = driver.page_source
    page = parse_page(html)
    corpus_key = (page["family"] or page["mtm"] or url.rstrip("/").split("/")[-1]).lower()
    
    html_path = CORPUS / f"{corpus_key}.html.gz"
    json_path = CORPUS / f"{corpus_key}.json"
    
    with gzip.open(html_path, "wt", encoding="utf-8") as f:
        f.write(html)
    page.update(url=url, scraped_at=datetime.now().isoformat(), server_name_hint=name_hint)
    json_path.write_text(json.dumps(page, ensure_ascii=False, indent=1), encoding="utf-8")
    
    print(f"     [SUCCESS] Saved {corpus_key}: family={page.get('family')} mtms={page.get('mtms')} published={page.get('published')}")
    print(f"     Top sections: {[n['title'] for n in page['tree']]}")
    return corpus_key


def main():
    parser = argparse.ArgumentParser(description="Scrape all IBM Power Sales Manuals")
    parser.add_argument("--force", action="store_true", help="Force re-scrape all servers")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of servers to scrape")
    args = parser.parse_args()

    driver = create_driver()
    success_count = 0
    fail_count = 0
    
    try:
        targets = SERVERS[:args.limit] if args.limit else SERVERS
        for i, s in enumerate(targets, 1):
            print(f"\n[{i}/{len(targets)}] {s['name']}")
            try:
                scrape_server(driver, s, force=args.force)
                success_count += 1
            except Exception as e:
                print(f"     [FAILED] {s['name']}: {e}")
                fail_count += 1
    finally:
        driver.quit()
        
    print(f"\n=== Scrape complete: {success_count} succeeded, {fail_count} failed ===")


if __name__ == "__main__":
    main()
