from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import traceback
import time
import re
from typing import List, Dict

app = Flask(__name__)

def html_table_to_markdown(table):
    """Convert HTML table to Markdown format"""
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
    """Extract withdrawal/discontinuation dates from text"""
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
    """Extract feature codes and their attributes from text"""
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


def scrape_ibm_docs_simple(url):
    """
    Enhanced scraper with table preservation and metadata extraction
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux ppc64le) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        print(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find content container
        content_div = soup.find('div', class_='ibmdocs-content-container')
        
        if not content_div:
            # Fallback to body
            content_div = soup.find('body')
        
        if not content_div:
            return {
                'success': False,
                'error': 'Could not find content',
                'html_length': len(response.content),
                'note': 'Page may require JavaScript rendering'
            }
        
        # Extract content with table preservation
        content_parts = []
        
        # Process tables first - convert to Markdown
        tables = content_div.find_all('table')
        for table in tables:
            markdown_table = html_table_to_markdown(table)
            if markdown_table:
                content_parts.append(f"\n{markdown_table}\n")
            # Replace table with placeholder
            table.replace_with(soup.new_string('[TABLE_EXTRACTED]'))
        
        # Extract text from other elements
        for elem in content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div']):
            text = elem.get_text(strip=True)
            if text and len(text) > 10 and '[TABLE_EXTRACTED]' not in text:
                content_parts.append(text)
        
        main_text = '\n\n'.join(content_parts)
        
        # Extract metadata
        title = soup.find('h1')
        full_text = soup.get_text()
        
        # Extract withdrawal dates
        withdrawal_dates = extract_withdrawal_dates(full_text)
        
        # Extract feature codes
        feature_codes = extract_feature_codes(full_text)
        
        # Extract sections
        headings = content_div.find_all(['h1', 'h2', 'h3', 'h4'])
        sections = []
        for heading in headings[:20]:
            section = {
                'level': heading.name,
                'title': heading.get_text(strip=True),
                'content': []
            }
            
            current = heading.find_next_sibling()
            count = 0
            while current and current.name not in ['h1', 'h2', 'h3', 'h4'] and count < 10:
                if current.name in ['p', 'ul', 'ol', 'table']:
                    text = current.get_text(strip=True)
                    if text:
                        section['content'].append(text[:500])
                current = current.find_next_sibling()
                count += 1
            
            if section['content']:
                sections.append(section)
        
        quality = calculate_quality(content_div)
        
        result = {
            'success': True,
            'method': 'Enhanced scraper with table preservation and metadata extraction',
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'page_title': title.get_text(strip=True) if title else None,
            'stats': {
                'paragraphs': len(content_div.find_all('p')),
                'headings': len(headings),
                'tables': len(tables),
                'tables_converted_to_markdown': len([p for p in content_parts if '|' in p and '---' in p]),
                'lists': len(content_div.find_all(['ul', 'ol'])),
                'sections': len(sections),
                'total_text_length': len(main_text),
                'html_length': len(response.content),
                'withdrawal_dates_found': len(withdrawal_dates),
                'feature_codes_found': len(feature_codes)
            },
            'sample_headings': [h.get_text(strip=True) for h in headings[:10]],
            'text_sample': main_text[:2000],
            'quality_score': quality,
            'sections_preview': sections[:5],
            'metadata': {
                'withdrawal_dates': withdrawal_dates,
                'feature_codes': feature_codes[:10]  # Limit to first 10
            },
            'note': 'Enhanced with table preservation (Markdown format) and metadata extraction'
        }
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'scraped_at': datetime.now().isoformat()
        }

def calculate_quality(content_div):
    """Calculate content quality score"""
    checks = {
        'has_paragraphs': len(content_div.find_all('p')) > 10,
        'has_headings': len(content_div.find_all(['h2', 'h3'])) > 5,
        'has_tables': len(content_div.find_all('table')) > 0,
        'has_lists': len(content_div.find_all(['ul', 'ol'])) > 0,
        'sufficient_content': len(content_div.get_text()) > 1000
    }
    score = sum(checks.values()) / len(checks) * 100
    return {
        'score': score,
        'checks': checks,
        'recommendation': get_recommendation(score)
    }

def get_recommendation(score):
    """Get recommendation based on quality score"""
    if score >= 80:
        return "Excellent - Content extracted successfully"
    elif score >= 60:
        return "Good - Partial content extracted"
    elif score >= 40:
        return "Fair - Limited content, may need JS rendering"
    else:
        return "Poor - Page requires JavaScript rendering. Consider using IBM Docs PDF export."

@app.route('/scrape-e1180')
def scrape_e1180():
    """Scrape IBM Power E1180 Sales Manual"""
    url = "https://www.ibm.com/docs/en/announcements/family-908005-power-e1180-enterprise-server-9080-heu"
    result = scrape_ibm_docs_simple(url)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/scrape')
def scrape_custom():
    """Scrape any IBM Docs URL"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: url',
            'usage': '/scrape?url=https://www.ibm.com/docs/...'
        }), 400
    
    result = scrape_ibm_docs_simple(url)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'IBM Docs Simple Scraper',
        'method': 'requests + BeautifulSoup (no JS rendering)',
        'note': 'For full content, use IBM Docs PDF export feature',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def index():
    """API documentation"""
    return jsonify({
        'service': 'IBM Docs Simple Scraper',
        'version': '1.0.0',
        'method': 'requests + BeautifulSoup (no JavaScript rendering)',
        'limitation': 'JavaScript-rendered content not available on ppc64le',
        'recommendation': 'Use IBM Docs PDF export for complete content',
        'endpoints': {
            '/health': 'Health check',
            '/scrape-e1180': 'Test scrape E1180 Sales Manual',
            '/scrape?url=<url>': 'Scrape any IBM Docs URL'
        },
        'pdf_approach': {
            'description': 'IBM Docs pages have a "Save as PDF" button that generates complete content',
            'advantage': 'PDFs contain all rendered content without needing JavaScript',
            'implementation': 'Download PDF programmatically and extract text with PyPDF2'
        }
    })

if __name__ == '__main__':
    print("Starting IBM Docs Simple Scraper Service...")
    print("Note: This scraper gets initial HTML only (no JS rendering)")
    print("For complete content, consider using IBM Docs PDF export feature")
    app.run(host='0.0.0.0', port=8080, debug=False)

# Made with Bob