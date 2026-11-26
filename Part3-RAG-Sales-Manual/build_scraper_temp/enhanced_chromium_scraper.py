"""
Enhanced Chromium Scraper for IBM Code Engine
Includes table preservation as Markdown and metadata extraction
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
import time
import re
import os
from datetime import datetime
from typing import List, Dict
import traceback

app = Flask(__name__)


def html_table_to_markdown(table: BeautifulSoup) -> str:
    """
    Convert HTML table to Markdown format
    
    Args:
        table: BeautifulSoup table element
        
    Returns:
        Markdown formatted table string
    """
    rows = []
    
    # Process header rows
    headers = []
    header_row = table.find('thead')
    if header_row:
        for th in header_row.find_all(['th', 'td']):
            headers.append(th.get_text(strip=True))
    else:
        # Try first row as header
        first_row = table.find('tr')
        if first_row:
            for th in first_row.find_all(['th', 'td']):
                headers.append(th.get_text(strip=True))
    
    if headers:
        rows.append('| ' + ' | '.join(headers) + ' |')
        rows.append('|' + '|'.join(['---' for _ in headers]) + '|')
    
    # Process body rows
    tbody = table.find('tbody') or table
    for tr in tbody.find_all('tr'):
        # Skip if this was the header row
        if headers and tr == table.find('tr'):
            continue
            
        cells = []
        for td in tr.find_all(['td', 'th']):
            cell_text = td.get_text(strip=True).replace('|', '\\|')  # Escape pipes
            cells.append(cell_text)
        
        if cells:
            rows.append('| ' + ' | '.join(cells) + ' |')
    
    return '\n'.join(rows)


def extract_withdrawal_dates(text: str) -> List[Dict[str, str]]:
    """
    Extract withdrawal/discontinuation dates from text
    
    Args:
        text: Text to search for dates
        
    Returns:
        List of dictionaries with date information
    """
    dates = []
    
    # Pattern for "No Longer Available as of DATE"
    pattern1 = r'No Longer Available as of ([A-Za-z]+ \d{1,2},? \d{4})'
    # Pattern for "Marketing Withdrawn" or "Service Discontinued" dates
    pattern2 = r'(Marketing Withdrawn|Service Discontinued)[:\s]+([A-Za-z]+ \d{1,2},? \d{4})'
    # Pattern for dates in parentheses with location
    pattern3 = r'\(For ([^)]+) - No Longer Available as of ([A-Za-z]+ \d{1,2},? \d{4})\)'
    
    for match in re.finditer(pattern1, text):
        dates.append({
            'type': 'withdrawal',
            'date': match.group(1),
            'location': 'general'
        })
    
    for match in re.finditer(pattern2, text):
        dates.append({
            'type': match.group(1).lower().replace(' ', '_'),
            'date': match.group(2),
            'location': 'general'
        })
    
    for match in re.finditer(pattern3, text):
        dates.append({
            'type': 'withdrawal',
            'date': match.group(2),
            'location': match.group(1)
        })
    
    return dates


def extract_feature_codes(text: str) -> List[Dict]:
    """
    Extract feature codes and their attributes from text
    
    Args:
        text: Text to search for feature codes
        
    Returns:
        List of dictionaries with feature code information
    """
    feature_codes = []
    
    # Pattern for feature codes like (#EFA1) or (EFA1)
    fc_pattern = r'\(#?([A-Z0-9]{4})\)\s+(.+?)(?=\n\n|\Z)'
    
    for match in re.finditer(fc_pattern, text, re.DOTALL):
        code = match.group(1)
        description = match.group(2).strip()
        
        # Extract attributes
        attributes = {}
        
        # Check for withdrawal date in description
        withdrawal_dates = extract_withdrawal_dates(description)
        if withdrawal_dates:
            attributes['withdrawal_dates'] = withdrawal_dates
        
        # Extract minimum/maximum values
        min_match = re.search(r'Minimum required:\s*(\d+)', description)
        if min_match:
            attributes['minimum_required'] = int(min_match.group(1))
        
        max_match = re.search(r'Maximum allowed:\s*(\d+)', description)
        if max_match:
            attributes['maximum_allowed'] = int(max_match.group(1))
        
        # Extract CSU status
        csu_match = re.search(r'CSU:\s*(Yes|No)', description)
        if csu_match:
            attributes['csu'] = csu_match.group(1) == 'Yes'
        
        feature_codes.append({
            'code': code,
            'description': description.split('\n')[0],  # First line only
            'full_text': description,
            'attributes': attributes
        })
    
    return feature_codes


def create_driver():
    """Create a headless Chrome WebDriver"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-extensions')
    # Spoof a real browser User-Agent — IBM's content API returns 403 to headless UA strings
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/128.0.0.0 Safari/537.36'
    )
    # Enable browser console log capture
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    # selenium/standalone-chrome image has Chrome at /opt/google/chrome/chrome
    options.binary_location = '/opt/google/chrome/chrome'

    # ChromeDriver is at /usr/bin/chromedriver in selenium/standalone-chrome
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)

    return driver


def scrape_ibm_docs_enhanced(url, wait_time=10):
    """
    Scrape IBM Docs page with enhanced table preservation and metadata extraction
    
    Args:
        url: IBM Docs page URL
        wait_time: Seconds to wait for JavaScript rendering
    
    Returns:
        dict: Scraped content with tables as Markdown and extracted metadata
    """
    driver = None
    try:
        driver = create_driver()
        
        # Load the page
        print(f"Loading URL: {url}")
        driver.get(url)

        # Step 1: Dismiss the TrustArc cookie consent banner immediately.
        # The banner has id="truste-consent-button" (the "Accept All" button).
        # Browser testing confirms: the IBM Docs content IS in the DOM while the
        # banner is visible, but clicking it clears the overlay promptly.
        # We do this first so the rest of the page can fully hydrate.
        print("Dismissing cookie consent banner (if present)...")
        try:
            accept_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "truste-consent-button"))
            )
            accept_btn.click()
            print("Cookie consent accepted (truste-consent-button).")
            time.sleep(2)
        except Exception:
            print("No cookie consent banner found (truste-consent-button) — continuing.")

        # Step 2: Wait for IBM Docs SPA to finish loading.
        # The page is a warmup.html shell — body is nearly empty at first load.
        # The IBM Docs JS app then makes async API calls to fetch content.
        # We wait on the actual DOM element appearing (not page_source string match)
        # which is more reliable, and allow up to 120s for a cold Code Engine network.
        print("Waiting for IBM Docs SPA content to render (up to 120s)...")
        try:
            WebDriverWait(driver, 120).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ibmdocs-content-container"))
            )
            print("ibmdocs-content-container found in DOM.")
        except Exception:
            # Fallback: check for any Sales Manual text signal in page source
            print("ibmdocs-content-container not found — checking page source for content signal...")
            try:
                WebDriverWait(driver, 30).until(
                    lambda d: "Product life cycle dates" in d.page_source or
                              "Sales manual" in d.page_source
                )
                print("Content signal found in page source.")
            except Exception as e:
                print(f"Warning: no content signal found after full wait: {e}")

        # Step 3: Additional wait for lazy-loaded sections and tables to populate
        time.sleep(wait_time)

        # Get the fully rendered HTML
        html = driver.page_source

        # Sanity check: bail out rather than storing garbage
        if "Product life cycle dates" not in html and "Sales manual" not in html and \
           "ibmdocs-content-container" not in html:
            return {
                'success': False,
                'error': 'IBM Docs SPA did not render content — timed out waiting for ibmdocs-content-container',
                'html_length': len(html)
            }

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Extract main content container
        content_div = (
            soup.find('div', class_='ibmdocs-content-container') or
            soup.find('div', class_='ibmdocs-topic') or
            soup.find('div', class_='content-wrapper') or
            soup.find('main') or
            soup.find('article') or
            soup.find('body')
        )

        if not content_div:
            return {
                'success': False,
                'error': 'Could not find content container',
                'html_length': len(html)
            }
        
        # Extract page title
        title = soup.find('h1')
        page_title = title.get_text(strip=True) if title else None
        
        # Extract all text for metadata extraction
        full_text = content_div.get_text(separator='\n', strip=True)
        
        # Extract metadata
        withdrawal_dates = extract_withdrawal_dates(full_text)
        feature_codes = extract_feature_codes(full_text)
        
        # Extract MTM from URL or title
        mtm = None
        mtm_match = re.search(r'(\d{4}-[A-Z0-9]{3})', url + ' ' + (page_title or ''))
        if mtm_match:
            mtm = mtm_match.group(1)
        
        # Process sections with enhanced table handling
        sections = []
        tables_as_markdown = []
        
        # Find all tables and convert to Markdown
        for table in content_div.find_all('table'):
            markdown_table = html_table_to_markdown(table)
            tables_as_markdown.append(markdown_table)
            # Replace table in content with Markdown version
            table.replace_with(BeautifulSoup(f'\n\n{markdown_table}\n\n', 'html.parser'))
        
        # Extract sections with hierarchy
        headings = content_div.find_all(['h1', 'h2', 'h3', 'h4'])
        
        for i, heading in enumerate(headings):
            section = {
                'level': int(heading.name[1]),  # h1 -> 1, h2 -> 2, etc.
                'title': heading.get_text(strip=True),
                'content': []
            }
            
            # Get content until next heading
            current = heading.find_next_sibling()
            while current and current.name not in ['h1', 'h2', 'h3', 'h4']:
                if current.name in ['p', 'ul', 'ol', 'div']:
                    text = current.get_text(strip=True)
                    if text:
                        section['content'].append(text)
                current = current.find_next_sibling() if current else None
            
            sections.append(section)
        
        # Get full text with Markdown tables
        full_text_with_tables = content_div.get_text(separator='\n', strip=True)
        
        result = {
            'success': True,
            'method': 'Enhanced Selenium + Chromium with Table Preservation',
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'page_title': page_title,
            'mtm': mtm,
            'html': html,
            'full_text': full_text_with_tables,
            'sections': sections,
            'sections_count': len(sections),
            'metadata': {
                'withdrawal_dates': withdrawal_dates,
                'feature_codes': feature_codes,
                'tables_count': len(tables_as_markdown),
                'has_structured_data': len(withdrawal_dates) > 0 or len(feature_codes) > 0
            },
            'tables_markdown': tables_as_markdown,
            'stats': {
                'paragraphs': len(content_div.find_all('p')),
                'headings': len(headings),
                'tables': len(tables_as_markdown),
                'lists': len(content_div.find_all(['ul', 'ol'])),
                'sections': len(sections),
                'total_text_length': len(full_text_with_tables),
                'html_length': len(html),
                'withdrawal_dates_found': len(withdrawal_dates),
                'feature_codes_found': len(feature_codes)
            }
        }
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'scraped_at': datetime.now().isoformat()
        }
    
    finally:
        if driver:
            driver.quit()


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Enhanced IBM Docs Scraper',
        'features': [
            'Table preservation as Markdown',
            'Withdrawal date extraction',
            'Feature code extraction',
            'MTM detection',
            'Structured sections'
        ],
        'timestamp': datetime.now().isoformat()
    })


@app.route('/scrape')
def scrape_custom():
    """Scrape any IBM Docs URL with enhanced features"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: url',
            'usage': '/scrape?url=https://www.ibm.com/docs/...'
        }), 400
    
    if 'ibm.com/docs' not in url:
        return jsonify({
            'success': False,
            'error': 'URL must be from ibm.com/docs domain'
        }), 400
    
    wait_time = request.args.get('wait', default=10, type=int)
    
    print(f"Starting scrape for URL: {url}")
    try:
        result = scrape_ibm_docs_enhanced(url, wait_time=wait_time)
        print(f"Scrape completed. Success: {result.get('success', False)}")
        
        if result['success']:
            return jsonify(result)
        else:
            print(f"Scrape failed with error: {result.get('error', 'Unknown error')}")
            if 'traceback' in result:
                print(f"Traceback:\n{result['traceback']}")
            return jsonify(result), 500
    except Exception as e:
        error_msg = f"Unexpected error in scrape_custom: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc()
        }), 500


@app.route('/classes')
def inspect_classes():
    """
    Diagnostic endpoint: load a page, dismiss cookie banner, wait, then return
    top CSS classes and content candidates. Used to diagnose DOM structure changes.
    """
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'missing url param'}), 400
    wait_time = request.args.get('wait', default=20, type=int)

    driver = None
    try:
        driver = create_driver()
        print(f"[classes] Loading: {url}  wait={wait_time}s")
        driver.get(url)

        # Wait for body
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Dismiss cookie banner — click id="truste-consent-button" (Accept All)
        try:
            btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "truste-consent-button"))
            )
            btn.click()
            print("[classes] Cookie consent accepted.")
            time.sleep(2)
        except Exception:
            print("[classes] No cookie banner found.")

        time.sleep(wait_time)  # let full JS render complete

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Capture browser console logs for diagnostics
        console_logs = []
        try:
            for entry in driver.get_log('browser'):
                console_logs.append(entry)
        except Exception:
            pass

        # Collect every CSS class token in the rendered page
        all_classes = []
        for tag in soup.find_all(True):
            for cls in tag.get('class', []):
                all_classes.append(cls)
        top_classes = [{'class': c, 'count': n} for c, n in Counter(all_classes).most_common(50)]

        # Find tags that look like content containers:
        # have a content/topic/docs/wrapper keyword in their class and hold >500 chars of text
        candidates = []
        seen_sigs = set()
        for tag in soup.find_all(True):
            cls_list = tag.get('class', [])
            cls_str = ' '.join(cls_list).lower()
            if any(kw in cls_str for kw in ['content', 'topic', 'article', 'wrapper', 'docs', 'body', 'main']):
                text_len = len(tag.get_text(strip=True))
                if text_len > 500:
                    sig = (tag.name, tuple(cls_list))
                    if sig not in seen_sigs:
                        seen_sigs.add(sig)
                        candidates.append({'tag': tag.name, 'classes': cls_list, 'text_len': text_len})
        candidates.sort(key=lambda x: -x['text_len'])
        candidates = candidates[:20]

        h1 = soup.find('h1')
        body_tag = soup.find('body')
        # Look for the Sales Manual signal text
        has_lifecycle = "Product life cycle dates" in html
        has_sales_manual = "Sales manual" in html
        return jsonify({
            'success': True,
            'url': url,
            'html_length': len(html),
            'page_title': h1.get_text(strip=True) if h1 else None,
            'has_lifecycle_text': has_lifecycle,
            'has_sales_manual_text': has_sales_manual,
            'top_classes': top_classes,
            'content_candidates': candidates,
            'body_html_snippet': str(body_tag)[:3000] if body_tag else '',
            'console_logs': console_logs[-30:],
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

# Made with Bob
