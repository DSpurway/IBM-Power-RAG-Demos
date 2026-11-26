"""
Diagnostic scraper: adds a /dump endpoint that returns top CSS classes 
from the rendered page without needing any content container match.
Deploy this temporarily to find what classes IBM are now using.
"""

from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from collections import Counter
import time, re, os, traceback
from datetime import datetime

app = Flask(__name__)


def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-extensions')
    options.binary_location = '/opt/google/chrome/chrome'
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'Diagnostic Scraper', 'timestamp': datetime.now().isoformat()})


@app.route('/dump')
def dump():
    """Load a page, wait 15s, return top classes and a snippet of the body HTML."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'missing url param'}), 400

    driver = None
    try:
        driver = create_driver()
        print(f"Loading: {url}")
        driver.get(url)

        # Just wait for body to be present (always true) then sleep
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(15)  # let JS fully render

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Collect all class tokens
        all_classes = []
        for tag in soup.find_all(True):
            for cls in tag.get('class', []):
                all_classes.append(cls)

        top_classes = Counter(all_classes).most_common(40)

        # Look for likely content containers
        candidates = []
        for tag in soup.find_all(True):
            cls_list = tag.get('class', [])
            cls_str = ' '.join(cls_list)
            # Heuristics: has 'content' or 'topic' or 'article' in class name, and has significant text
            if any(kw in cls_str.lower() for kw in ['content', 'topic', 'article', 'body', 'main', 'wrapper', 'docs']):
                text_len = len(tag.get_text(strip=True))
                if text_len > 500:
                    candidates.append({
                        'tag': tag.name,
                        'classes': cls_list,
                        'text_len': text_len
                    })

        # Deduplicate candidates by class signature, keep top by text_len
        seen = set()
        unique_candidates = []
        for c in sorted(candidates, key=lambda x: -x['text_len']):
            key = tuple(c['classes'])
            if key not in seen:
                seen.add(key)
                unique_candidates.append(c)
            if len(unique_candidates) >= 15:
                break

        # Also grab the h1 title
        h1 = soup.find('h1')
        page_title = h1.get_text(strip=True) if h1 else None

        # Snippet of body HTML (first 2000 chars of body inner HTML)
        body = soup.find('body')
        body_snippet = str(body)[:2000] if body else ''

        return jsonify({
            'success': True,
            'url': url,
            'html_length': len(html),
            'page_title': page_title,
            'top_classes': [{'class': c, 'count': n} for c, n in top_classes],
            'content_candidates': unique_candidates,
            'body_html_snippet': body_snippet,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
