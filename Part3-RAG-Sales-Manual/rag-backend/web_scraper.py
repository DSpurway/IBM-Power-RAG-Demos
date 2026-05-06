"""
Web Scraper for IBM Documentation Pages
Extracts content from IBM Docs pages for ingestion into vector database
Enhanced with table preservation and metadata extraction
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
import logging
from urllib.parse import urlparse
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class IBMDocsScraperError(Exception):
    """Custom exception for scraping errors"""
    pass


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


def extract_feature_codes(text: str) -> List[Dict[str, any]]:  # type: ignore
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


class IBMDocsScraper:
    """Scraper for IBM Documentation pages with enhanced table and metadata extraction"""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the scraper
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_page(self, url: str) -> str:
        """
        Fetch HTML content from URL
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string
            
        Raises:
            IBMDocsScraperError: If fetch fails
        """
        try:
            logger.info(f"Fetching URL: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise IBMDocsScraperError(f"Failed to fetch URL {url}: {str(e)}")
    
    def extract_main_content(self, html: str, url: str) -> Dict[str, any]:  # type: ignore
        """
        Extract main content from IBM Docs page
        
        Args:
            html: HTML content
            url: Source URL
            
        Returns:
            Dictionary with extracted content
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = self._extract_title(soup)
        
        # Extract main content
        content = self._extract_content(soup)
        
        # Extract metadata
        metadata = self._extract_metadata(soup, url)
        
        return {
            'title': title,
            'content': content,
            'metadata': metadata,
            'url': url
        }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        # Try multiple selectors for IBM Docs pages
        title_selectors = [
            'h1.bx--type-productive-heading-05',
            'h1.title',
            'h1',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                return title_elem.get_text(strip=True)
        
        return "Untitled"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from IBM Docs page with table preservation
        
        IBM Docs pages typically use specific content containers
        """
        content_parts = []
        
        # Try to find main content area
        content_selectors = [
            'div.bx--content',
            'main',
            'article',
            'div.content',
            'div#content',
            'div.main-content'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                logger.info(f"Found content using selector: {selector}")
                break
        
        if not main_content:
            # Fallback: use body
            main_content = soup.body
            logger.warning("Using body as fallback for content extraction")
        
        if main_content:
            # Remove unwanted elements
            for unwanted in main_content.select('script, style, nav, header, footer, .navigation, .breadcrumb'):
                unwanted.decompose()
            
            # Process tables first - convert to Markdown
            for table in main_content.find_all('table'):
                markdown_table = html_table_to_markdown(table)
                if markdown_table:
                    content_parts.append(f"\n{markdown_table}\n")
                # Replace table with placeholder to avoid duplicate extraction
                table.replace_with(soup.new_string('[TABLE_EXTRACTED]'))
            
            # Extract text from other elements
            for elem in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div']):
                text = elem.get_text(strip=True)
                # Skip empty text and table placeholders
                if text and len(text) > 10 and '[TABLE_EXTRACTED]' not in text:
                    content_parts.append(text)
        
        content = '\n\n'.join(content_parts)
        
        if not content:
            raise IBMDocsScraperError("No content extracted from page")
        
        logger.info(f"Extracted {len(content)} characters of content with {content.count('|')} table cells")
        return content
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, any]:  # type: ignore
        """Extract metadata from page including withdrawal dates and feature codes"""
        metadata: Dict[str, any] = {  # type: ignore
            'source': url,
            'source_type': 'web_page'
        }
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and hasattr(meta_desc, 'get') and meta_desc.get('content'):
            metadata['description'] = meta_desc.get('content')
        
        # Extract meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and hasattr(meta_keywords, 'get') and meta_keywords.get('content'):
            metadata['keywords'] = meta_keywords.get('content')
        
        # Extract publication date if available
        date_elem = soup.find('meta', attrs={'name': 'DC.date'})
        if date_elem and hasattr(date_elem, 'get') and date_elem.get('content'):
            metadata['publication_date'] = date_elem.get('content')
        
        # Parse URL for additional metadata
        parsed_url = urlparse(url)
        metadata['domain'] = parsed_url.netloc
        
        # Extract full text for advanced metadata extraction
        full_text = soup.get_text()
        
        # Extract withdrawal dates
        withdrawal_dates = extract_withdrawal_dates(full_text)
        if withdrawal_dates:
            metadata['withdrawal_dates'] = withdrawal_dates
            logger.info(f"Found {len(withdrawal_dates)} withdrawal dates")
        
        # Extract feature codes
        feature_codes = extract_feature_codes(full_text)
        if feature_codes:
            metadata['feature_codes'] = feature_codes
            logger.info(f"Found {len(feature_codes)} feature codes")
        
        return metadata
    
    def scrape_url(self, url: str) -> Dict[str, any]:  # type: ignore
        """
        Scrape a single URL and return structured content
        
        Args:
            url: URL to scrape
            
        Returns:
            Dictionary with title, content, metadata, and url
        """
        html = self.fetch_page(url)
        return self.extract_main_content(html, url)
    
    def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, any]]:  # type: ignore
        """
        Scrape multiple URLs
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of dictionaries with scraped content
        """
        results = []
        for url in urls:
            try:
                result = self.scrape_url(url)
                results.append(result)
            except IBMDocsScraperError as e:
                logger.error(f"Failed to scrape {url}: {e}")
                # Continue with other URLs
        
        return results


def create_langchain_documents(scraped_data: Dict[str, any]) -> List:  # type: ignore
    """
    Convert scraped data to LangChain Document format
    
    Args:
        scraped_data: Dictionary from scrape_url()
        
    Returns:
        List of LangChain Document objects
    """
    from langchain.schema import Document
    
    # Create a single document with the full content
    # The text splitter will handle chunking later
    doc = Document(
        page_content=f"# {scraped_data['title']}\n\n{scraped_data['content']}",
        metadata=scraped_data['metadata']
    )
    
    return [doc]

# Made with Bob
