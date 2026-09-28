"""
IBM Power Announcements Scanner & Ingestion Service
Scans https://www.ibm.com/support/pages/ibm-power-announcements for new announcements,
detects deltas via content hashes / announcement IDs, scrapes full announcement letters,
extracts affected MTMs / Feature codes, and chunks them into the OpenSearch announcements collection.
"""

import os
import re
import time
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ANNOUNCEMENTS_INDEX_URL = "https://www.ibm.com/support/pages/ibm-power-announcements"
ANNOUNCEMENTS_COLLECTION_NAME = "rag_power_announcements"

# Common MTM patterns (e.g. 9080-HEX, 9080-HEU, 9009-42A, 9105-42A, 9028-21B, 9043-MRX)
MTM_REGEX = re.compile(r'\b(\d{4}-[A-Z0-9]{3})\b', re.IGNORECASE)
FEATURE_CODE_REGEX = re.compile(r'(?:#|\bfeature\s+code\s+|\bfeature\s+)([A-Z0-9]{4})\b', re.IGNORECASE)
POWER_GEN_REGEX = re.compile(r'\b(Power[789]|Power1[012]|POWER[789]|POWER1[012])\b', re.IGNORECASE)


class AnnouncementScannerService:
    def __init__(self, opensearch_client=None, embeddings_model=None, scraper_url=None):
        self.opensearch_client = opensearch_client
        self.embeddings_model = embeddings_model
        self.scraper_url = scraper_url or os.getenv(
            "SCRAPER_URL", 
            "https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud"
        )
        self.collection_name = ANNOUNCEMENTS_COLLECTION_NAME

    def fetch_announcements_index(self) -> List[Dict[str, Any]]:
        """
        Fetch the top-level IBM Power Announcements support page and parse the hierarchical twisties.
        Returns a structured list of announcement records.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        logger.info(f"Fetching announcements index from {ANNOUNCEMENTS_INDEX_URL}...")
        resp = requests.get(ANNOUNCEMENTS_INDEX_URL, headers=headers, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Calculate a checksum of the raw announcement section HTML to detect top-level page updates
        content_div = soup.find('p', class_='ibm-northstart-documentation-information-data') or soup.find('body')
        raw_html = str(content_div) if content_div else resp.text
        index_hash = hashlib.sha256(raw_html.encode('utf-8')).hexdigest()
        
        announcements = []
        
        # Traverse year panels -> quarter panels -> month headers -> ul/li links
        # Structure pattern: div.ibm-show-hide (h2: Year) -> div (h2: Quarter) -> h2: Month -> ul -> li -> a[href]
        year_panels = soup.find_all('div', class_='ibm-show-hide')
        
        for yp in year_panels:
            year_h2 = yp.find('h2')
            year_str = year_h2.get_text(strip=True) if year_h2 else None
            
            quarter_divs = yp.find_all('div', class_='ibm-show-hide')
            for qd in quarter_divs:
                quarter_h2 = qd.find('h2')
                quarter_str = quarter_h2.get_text(strip=True) if quarter_h2 else None
                
                # Within the quarter container, find month headings and following uls
                current_month = "Unknown"
                for elem in qd.find_all(['h2', 'ul']):
                    if elem.name == 'h2':
                        current_month = elem.get_text(strip=True)
                    elif elem.name == 'ul':
                        for li in elem.find_all('li'):
                            a_tag = li.find('a')
                            if not a_tag or not a_tag.get('href'):
                                continue
                            
                            url = a_tag['href'].strip()
                            title = a_tag.get_text(strip=True)
                            
                            # Extract announcement ID (e.g. AD26-0873, AD25-1733)
                            id_match = re.search(r'([A-Z]{2}\d{2}-\d{4})', url + ' ' + title)
                            announcement_id = id_match.group(1) if id_match else url.split('/')[-1]
                            
                            # Determine category
                            category = "General Announcement"
                            lower_title = title.lower()
                            if "hardware withdrawal" in lower_title or "withdrawal:" in lower_title:
                                category = "Hardware Withdrawal"
                            elif "software withdrawal" in lower_title:
                                category = "Software Withdrawal"
                            elif "enhancement" in lower_title or "introduces" in lower_title or "expands" in lower_title:
                                category = "Enhancement / New Offering"
                            elif "statement of direction" in lower_title:
                                category = "Statement of Direction"
                            elif "revised availability" in lower_title or "service support level" in lower_title:
                                category = "Lifecycle / Support Level"
                            
                            # Construct announcement entry
                            announcements.append({
                                'announcement_id': announcement_id,
                                'title': title,
                                'url': url,
                                'year': year_str,
                                'quarter': quarter_str,
                                'month': current_month,
                                'category': category,
                                'index_page_hash': index_hash
                            })
        
        logger.info(f"Discovered {len(announcements)} total announcements from index page (hash={index_hash[:8]}).")
        return announcements

    def extract_metadata_from_text(self, text: str, title: str = "") -> Dict[str, Any]:
        """
        Extract affected MTMs, Feature Codes, Power Generations, and Withdrawal Dates from text.
        """
        combined = f"{title}\n{text}"
        
        # MTMs
        mtm_matches = list(set(m.upper() for m in MTM_REGEX.findall(combined)))
        
        # Feature codes
        fc_matches = list(set(fc.upper() for fc in FEATURE_CODE_REGEX.findall(combined)))
        
        # Power generations
        gen_matches = list(set(g.upper() for g in POWER_GEN_REGEX.findall(combined)))
        
        return {
            'applicable_mtms': mtm_matches,
            'feature_codes': fc_matches,
            'power_generations': gen_matches
        }

    def scrape_announcement(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrapes a single announcement letter using the enhanced scraper service.
        """
        try:
            logger.info(f"Scraping announcement letter at {url}...")
            endpoint = f"{self.scraper_url.rstrip('/')}/scrape"
            resp = requests.get(endpoint, params={'url': url, 'wait': 6}, timeout=45)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    return data
            logger.warning(f"Scraper returned status {resp.status_code} for {url}")
            return None
        except Exception as e:
            logger.error(f"Error scraping announcement {url}: {e}")
            return None

    def chunk_announcement(self, announcement: Dict[str, Any], scraped_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Breaks down an announcement letter into semantic chunks tagged with rich metadata.
        """
        chunks = []
        full_text = scraped_data.get('full_text', '')
        sections = scraped_data.get('sections', [])
        
        # Extract global announcement metadata
        extracted_meta = self.extract_metadata_from_text(full_text, announcement.get('title', ''))
        
        chunk_idx = 0
        
        # If structured sections exist, chunk by section
        if sections and len(sections) > 1:
            for sec in sections:
                sec_title = sec.get('title', '')
                sec_content = '\n'.join(sec.get('content', []))
                
                if not sec_content.strip():
                    continue
                
                # Check section-specific MTMs
                sec_meta = self.extract_metadata_from_text(sec_content, sec_title)
                combined_mtms = list(set(extracted_meta['applicable_mtms'] + sec_meta['applicable_mtms']))
                
                chunk_text = f"Announcement: {announcement['title']} ({announcement['announcement_id']})\n" \
                             f"Date: {announcement.get('month', '')} {announcement.get('year', '')} ({announcement.get('quarter', '')})\n" \
                             f"Category: {announcement.get('category', 'General')}\n" \
                             f"Section: {sec_title}\n\n{sec_content}"
                
                chunks.append({
                    'chunk_index': chunk_idx,
                    'text': chunk_text,
                    'metadata': {
                        'type': 'announcement',
                        'announcement_id': announcement['announcement_id'],
                        'title': announcement['title'],
                        'source': announcement['url'],
                        'year': announcement.get('year'),
                        'quarter': announcement.get('quarter'),
                        'month': announcement.get('month'),
                        'category': announcement.get('category'),
                        'section_title': sec_title,
                        'applicable_mtms': combined_mtms,
                        'feature_codes': sec_meta['feature_codes'],
                        'power_generations': extracted_meta['power_generations'],
                        'created_at': datetime.utcnow().isoformat()
                    }
                })
                chunk_idx += 1
        else:
            # Chunk long full text by paragraphs (~1500 chars with 200 char overlap)
            paragraphs = full_text.split('\n\n')
            current_chunk = []
            current_len = 0
            
            for p in paragraphs:
                p_clean = p.strip()
                if not p_clean:
                    continue
                
                current_chunk.append(p_clean)
                current_len += len(p_clean)
                
                if current_len >= 1200:
                    chunk_body = '\n\n'.join(current_chunk)
                    chunk_text = f"Announcement: {announcement['title']} ({announcement['announcement_id']})\n" \
                                 f"Date: {announcement.get('month', '')} {announcement.get('year', '')} ({announcement.get('quarter', '')})\n" \
                                 f"Category: {announcement.get('category', 'General')}\n\n{chunk_body}"
                    
                    chunks.append({
                        'chunk_index': chunk_idx,
                        'text': chunk_text,
                        'metadata': {
                            'type': 'announcement',
                            'announcement_id': announcement['announcement_id'],
                            'title': announcement['title'],
                            'source': announcement['url'],
                            'year': announcement.get('year'),
                            'quarter': announcement.get('quarter'),
                            'month': announcement.get('month'),
                            'category': announcement.get('category'),
                            'applicable_mtms': extracted_meta['applicable_mtms'],
                            'feature_codes': extracted_meta['feature_codes'],
                            'power_generations': extracted_meta['power_generations'],
                            'created_at': datetime.utcnow().isoformat()
                        }
                    })
                    chunk_idx += 1
                    current_chunk = []
                    current_len = 0
            
            if current_chunk:
                chunk_body = '\n\n'.join(current_chunk)
                chunk_text = f"Announcement: {announcement['title']} ({announcement['announcement_id']})\n" \
                             f"Date: {announcement.get('month', '')} {announcement.get('year', '')} ({announcement.get('quarter', '')})\n" \
                             f"Category: {announcement.get('category', 'General')}\n\n{chunk_body}"
                chunks.append({
                    'chunk_index': chunk_idx,
                    'text': chunk_text,
                    'metadata': {
                        'type': 'announcement',
                        'announcement_id': announcement['announcement_id'],
                        'title': announcement['title'],
                        'source': announcement['url'],
                        'year': announcement.get('year'),
                        'quarter': announcement.get('quarter'),
                        'month': announcement.get('month'),
                        'category': announcement.get('category'),
                        'applicable_mtms': extracted_meta['applicable_mtms'],
                        'feature_codes': extracted_meta['feature_codes'],
                        'power_generations': extracted_meta['power_generations'],
                        'created_at': datetime.utcnow().isoformat()
                    }
                })
        
        return chunks
