"""
Smart Hierarchical Chunker for IBM Sales Manuals
Preserves table structure for direct lookup and creates semantic chunks for RAG
"""

import re
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Fixed list of known major section headings used as section boundaries.
# Using a fixed list prevents the regex from treating any short Title Case line
# (e.g. a table header or product name) as a section boundary.
MAJOR_SECTIONS = [
    'Abstract', 'Highlights', 'Description', 'Models',
    'Technical description', 'Publications', 'Features',
    'Feature descriptions', 'Accessories', 'Supplies',
    'Trademarks', 'Specifications', 'Product life cycle dates',
    'Product positioning',
]

class SalesManualChunker:
    """
    Intelligent chunker for IBM Power Sales Manual pages
    Preserves table structure and creates semantically meaningful chunks
    """
    
    def __init__(self, max_chunk_size=1500, overlap=100):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        # Paragraph-first splitter — prefers \n\n boundaries so sentences are
        # not cut mid-way. Character count is the last resort.
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk_sales_manual(self, full_text: str, server_name: str, mtm: str, url: str, sections: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """
        Main chunking method - processes entire Sales Manual
        
        Args:
            full_text: Complete scraped text from Sales Manual page
            server_name: Server name (e.g., "IBM Power System S924")
            mtm: Machine Type-Model (e.g., "9009-42A")
            url: Source URL
            sections: Optional structured sections from scraper (list of dicts with 'title', 'content', 'level')
            
        Returns:
            List of chunks with text and metadata
        """
        chunks = []
        
        # Calculate content hash for change detection
        content_hash = hashlib.sha256(full_text.encode('utf-8')).hexdigest()
        ingestion_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Common metadata for all chunks (for change detection)
        common_metadata = {
            'content_hash': content_hash,
            'content_length': len(full_text),
            'ingestion_timestamp': ingestion_timestamp,
            'chunker_version': '1.1.0'
        }
        
        # 1. Extract and preserve lifecycle table (CRITICAL for direct lookup)
        lifecycle_chunk = self._extract_lifecycle_table(full_text, server_name, mtm, url, common_metadata)
        if lifecycle_chunk:
            chunks.append(lifecycle_chunk)
            logger.info(f"✓ Extracted lifecycle table for {mtm}")
        
        # 2. Extract feature codes with metadata (for metadata search)
        # Use structured sections if available, otherwise fall back to full_text
        if sections:
            feature_chunks = self._extract_feature_codes_from_sections(sections, server_name, mtm, url, common_metadata)
            logger.info(f"✓ Extracted {len(feature_chunks)} feature codes from structured sections for {mtm}")
        else:
            feature_chunks = self._extract_feature_codes_fallback(full_text, server_name, mtm, url, common_metadata)
            logger.info(f"✓ Extracted {len(feature_chunks)} feature codes from full text for {mtm}")
        chunks.extend(feature_chunks)
        
        # 3. Extract other sections for RAG
        section_chunks = self._extract_sections(full_text, server_name, mtm, url, common_metadata)
        chunks.extend(section_chunks)
        logger.info(f"✓ Extracted {len(section_chunks)} section chunks for {mtm}")
        
        logger.info(f"Total chunks created for {mtm}: {len(chunks)} (hash: {content_hash[:8]}...)")
        return chunks
    
    def _extract_lifecycle_table(self, text: str, server_name: str, mtm: str, url: str, common_metadata: Dict) -> Optional[Dict]:
        """
        Extract lifecycle table and preserve as Markdown for direct parsing
        This enables fast, accurate responses without LLM
        """
        # Look for "Product lifecycle dates" or "Product life cycle dates"
        # Extract ONLY the table rows (lines starting with |), nothing else
        table_pattern = r'Product\s+life\s*cycle\s+dates\s*\n+((?:\|[^\n]+\|\n?)+)'
        match = re.search(table_pattern, text, re.IGNORECASE)
        
        if not match:
            logger.warning(f"No lifecycle table found for {mtm}")
            return None
        
        # Extract just the table rows (all lines starting with |)
        table_rows = match.group(1).strip()
        
        # Build clean table with header
        table_text = "Product life cycle dates\n" + table_rows
        
        # Check if it's already in table format (with | separators)
        if '|' in table_text:
            # Already Markdown table - preserve as-is
            formatted_table = table_text
        else:
            # Convert to Markdown table format
            formatted_table = self._format_as_markdown_table(table_text)
        
        return {
            'text': formatted_table,
            'metadata': {
                'section_type': 'lifecycle_table',
                'section_title': 'Product lifecycle dates',
                'server_name': server_name,
                'mtm': mtm,
                'source': url,
                'priority': 'critical',
                'query_type': 'direct_lookup',  # No LLM needed
                'chunk_strategy': 'preserve_table_structure',
                **common_metadata  # Add change detection metadata
            }
        }
    
    def _format_as_markdown_table(self, table_text: str) -> str:
        """Convert plain text table to Markdown format"""
        lines = table_text.split('\n')
        
        # Find header and data rows
        header_line = None
        data_lines = []
        
        for line in lines:
            if 'Type Model' in line or 'Announced' in line:
                header_line = line
            elif re.search(r'\d{4}-\d{2}-\d{2}', line):  # Has date format
                data_lines.append(line)
        
        if not header_line or not data_lines:
            return table_text  # Return as-is if can't parse
        
        # Build Markdown table
        markdown_lines = ['Product lifecycle dates\n']
        
        # Header
        headers = re.split(r'\s{2,}|\t', header_line.strip())
        markdown_lines.append('| ' + ' | '.join(headers) + ' |')
        markdown_lines.append('|' + '|'.join(['---' for _ in headers]) + '|')
        
        # Data rows
        for line in data_lines:
            cells = re.split(r'\s{2,}|\t', line.strip())
            markdown_lines.append('| ' + ' | '.join(cells) + ' |')
        
        return '\n'.join(markdown_lines)
    
    def _extract_feature_codes_from_sections(self, sections: List[Dict], server_name: str, mtm: str, url: str, common_metadata: Dict) -> List[Dict]:
        """
        Extract feature codes from structured sections data
        Looks for sections with titles matching (#XXXX) pattern
        
        IMPORTANT: Only extracts from "Feature descriptions" subsection,
        ignoring all other sections including "Features - Chargeable",
        "Feature availability matrix", etc.
        """
        chunks = []
        
        # Track if we're in the Feature descriptions subsection specifically
        in_feature_descriptions = False
        
        for section in sections:
            title = section.get('title', '')
            content = section.get('content', [])
            level = section.get('level', 0)
            
            # Check if we've entered the "Feature descriptions" subsection
            # This is the ONLY place we extract feature codes from
            if 'Feature descriptions' in title or 'Feature description' in title:
                in_feature_descriptions = True
                logger.info(f"Entered Feature descriptions section for {mtm}")
                continue
            
            # Exit Feature descriptions if we hit a new major section at same or higher level
            # that doesn't start with (#
            if in_feature_descriptions and level <= 2 and not title.startswith('(#'):
                # Check if this is a new major section (Accessories, Supplies, etc.)
                if any(keyword in title for keyword in ['Accessories', 'Supplies', 'Trademarks', 'Publications', 'Specifications']):
                    in_feature_descriptions = False
                    logger.info(f"Exited Feature descriptions section at: {title}")
                    continue
            
            # Check if this is a feature code section: (#XXXX) or (#XXXX) - Feature Name
            feature_match = re.match(r'\(#([A-Z0-9]{4})\)\s*-?\s*(.*)', title)
            if not feature_match:
                continue
            
            # ONLY process feature codes if we're in the Feature descriptions subsection
            if not in_feature_descriptions:
                logger.debug(f"Skipping feature code {feature_match.group(1)} - not in Feature descriptions section (found in: {title})")
                continue
            
            feature_code = feature_match.group(1)
            feature_name = feature_match.group(2).strip() if feature_match.group(2) else ''
            
            # Skip list items: titles starting with dash like "(#0004) -EMEA Bulk MES Indicator"
            # These are references in lists, not full descriptions
            if feature_name.startswith('-'):
                logger.debug(f"Skipping feature code {feature_code} - list item (starts with dash): {title}")
                continue
            
            # Join content paragraphs
            feature_details = '\n\n'.join(content) if content else ''
            
            # Skip if no content
            if not feature_details:
                logger.debug(f"Skipping feature code {feature_code} - no content")
                continue
            
            # Extract structured metadata
            metadata = self._parse_feature_metadata(feature_details)
            
            # Build chunk text with full description
            chunk_text = f"(#{feature_code}) {feature_name}\n\n{feature_details}"
            
            chunks.append({
                'text': chunk_text,
                'metadata': {
                    'section_type': 'feature_code',
                    'section_title': 'Feature descriptions',
                    'feature_code': feature_code,
                    'feature_name': feature_name,
                    'server_name': server_name,
                    'mtm': mtm,
                    'source': url,
                    'priority': 'high',
                    'query_type': 'metadata_search',
                    'chunk_strategy': 'structured_section',
                    'section_level': level,
                    **metadata,  # Add parsed metadata (withdrawal_date, csu, etc.)
                    **common_metadata  # Add change detection metadata
                }
            })
        
        logger.info(f"Extracted {len(chunks)} feature codes for {mtm}")
        return chunks
    def _extract_feature_codes_fallback(self, text: str, server_name: str, mtm: str, url: str, common_metadata: Dict) -> List[Dict]:
        """
        FALLBACK: Extract feature codes from plain text when structured sections not available
        This is a simplified fallback - structured sections are preferred
        """
        chunks = []
        logger.warning(f"Using fallback plain text feature extraction for {mtm} - structured sections not available")
        
        # Simple pattern matching for feature codes in plain text
        # Pattern: (#XXXX) followed by text until next (#XXXX) or major section
        feature_pattern = r'\(#([A-Z0-9]{4})\)\s*-?\s*([^\n]+)(.*?)(?=\(#[A-Z0-9]{4}\)|\n\n[A-Z][a-z]+\s+[a-z]+\s*\n|\Z)'
        
        for match in re.finditer(feature_pattern, text, re.DOTALL):
            feature_code = match.group(1)
            feature_name = match.group(2).strip()
            feature_details = match.group(3).strip()
            
            if not feature_details:
                continue
            
            # Extract structured metadata
            metadata = self._parse_feature_metadata(feature_details)
            
            # Build chunk text
            chunk_text = f"(#{feature_code}) {feature_name}\n\n{feature_details}"
            
            chunks.append({
                'text': chunk_text,
                'metadata': {
                    'section_type': 'feature_code',
                    'section_title': 'Feature descriptions',
                    'feature_code': feature_code,
                    'feature_name': feature_name,
                    'server_name': server_name,
                    'mtm': mtm,
                    'source': url,
                    'priority': 'high',
                    'query_type': 'metadata_search',
                    'chunk_strategy': 'fallback_plain_text',
                    **metadata,
                    **common_metadata
                }
            })
        
        return chunks
    
    
    def _parse_feature_metadata(self, details: str) -> Dict[str, Any]:
        """Parse structured metadata from feature details"""
        metadata = {}
        
        # Withdrawal date
        withdrawal_match = re.search(
            r'[Nn]o longer available as of ([A-Za-z]+ \d+,?\s*\d{4})',
            details
        )
        if withdrawal_match:
            metadata['withdrawal_date'] = withdrawal_match.group(1)
            metadata['is_withdrawn'] = True
        else:
            metadata['is_withdrawn'] = False
        
        # CSU (Customer Setup)
        csu_match = re.search(r'CSU:\s*(Yes|No)', details, re.IGNORECASE)
        if csu_match:
            metadata['csu'] = csu_match.group(1).lower() == 'yes'
        
        # Minimum/Maximum values
        min_match = re.search(r'Minimum required:\s*(\d+)', details)
        if min_match:
            metadata['minimum_required'] = int(min_match.group(1))
        
        max_match = re.search(r'Maximum allowed:\s*(\d+)', details)
        if max_match:
            metadata['maximum_allowed'] = int(max_match.group(1))
        
        return metadata
    
    def _extract_sections(self, text: str, server_name: str, mtm: str, url: str, common_metadata: Dict) -> List[Dict]:
        """
        Extract other sections for RAG queries (NOT feature codes)
        These require LLM for synthesis and complex queries
        
        Note: Feature codes are extracted separately via structured sections
        to avoid duplicates and ensure accurate metadata extraction
        """
        chunks = []
        
        # Define section patterns and chunking strategies
        # NOTE: We do NOT extract feature codes here - they come from structured sections
        sections_config = {
            'Abstract': {'strategy': 'keep_intact', 'priority': 'high'},
            'Highlights': {'strategy': 'split_if_large', 'priority': 'medium'},
            'Description': {'strategy': 'split_if_large', 'priority': 'medium'},
            'Product positioning': {'strategy': 'keep_intact', 'priority': 'medium'},
            'Models': {'strategy': 'keep_intact', 'priority': 'high'},
            'Technical description': {'strategy': 'split_if_large', 'priority': 'high'},
            'Accessories': {'strategy': 'keep_intact', 'priority': 'low'}
        }
        
        for section_name, config in sections_config.items():
            section_text = self._find_section(text, section_name)
            if not section_text:
                continue
            
            # Clean the section text - remove metadata artifacts
            section_text = self._clean_section_text(section_text)
            
            strategy = config['strategy']
            
            if strategy == 'keep_intact':
                chunks.append(self._create_chunk(
                    section_name, section_text, server_name, mtm, url,
                    priority=config['priority'], strategy='keep_intact',
                    common_metadata=common_metadata
                ))
            
            elif strategy == 'split_if_large':
                if len(section_text) > self.max_chunk_size:
                    sub_chunks = self.text_splitter.split_text(section_text)
                    for i, sub_chunk in enumerate(sub_chunks):
                        # Don't add (Part X/Y) to chunk text - keep it clean for search
                        chunks.append(self._create_chunk(
                            section_name,
                            sub_chunk, server_name, mtm, url,
                            priority=config['priority'], strategy='split_large',
                            part_index=i, total_parts=len(sub_chunks),
                            common_metadata=common_metadata
                        ))
                else:
                    chunks.append(self._create_chunk(
                        section_name, section_text, server_name, mtm, url,
                        priority=config['priority'], strategy='keep_intact',
                        common_metadata=common_metadata
                    ))
            
            elif strategy == 'split_by_subheading':
                sub_chunks = self._split_by_subheadings(section_text, section_name)
                for sub_name, sub_text in sub_chunks:
                    # Include subheading in chunk text for better context
                    chunk_text_with_heading = f"{sub_name}\n\n{sub_text}"
                    chunks.append(self._create_chunk(
                        f"{section_name} - {sub_name}",
                        chunk_text_with_heading, server_name, mtm, url,
                        priority=config['priority'], strategy='subheading_split',
                        subsection=sub_name,
                        common_metadata=common_metadata
                    ))
            
            elif strategy == 'split_by_paragraph':
                sub_chunks = self.text_splitter.split_text(section_text)
                for i, sub_chunk in enumerate(sub_chunks):
                    # Don't add (Part X/Y) to chunk text - keep it clean for search
                    chunks.append(self._create_chunk(
                        section_name,
                        sub_chunk, server_name, mtm, url,
                        priority=config['priority'], strategy='paragraph_split',
                        part_index=i, total_parts=len(sub_chunks),
                        common_metadata=common_metadata
                    ))
        
        return chunks
    
    def _find_section(self, text: str, section_name: str) -> Optional[str]:
        """
        Find a section by name in the text.
        Section boundaries are detected using MAJOR_SECTIONS — a fixed list of
        known headings — rather than a generic Title Case regex that would
        incorrectly split on product names, table headers, etc.
        Skips "Feature descriptions" entirely (handled by structured extraction).
        """
        # SKIP "Feature descriptions" section — feature codes extracted separately
        if 'Feature description' in section_name:
            logger.debug(f"Skipping '{section_name}' section - feature codes extracted separately via structured sections")
            return None

        # Build alternation of all *other* major section names as boundary anchors
        other_sections = [s for s in MAJOR_SECTIONS if s.lower() != section_name.lower()]
        boundary = '|'.join(re.escape(s) for s in other_sections)

        # Primary pattern: section heading on its own line, content up to any
        # other known major section heading (also on its own line) or EOF.
        pattern = rf'^{re.escape(section_name)}\s*$\n+(.*?)(?=\n^(?:{boundary})\s*$|\Z)'
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)

        if not match:
            # Fallback: looser anchoring without strict line boundaries
            pattern = rf'{re.escape(section_name)}\s*\n+(.*?)(?=\n(?:{boundary})\n|\Z)'
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if not match:
            return None

        section_text = match.group(1).strip()
        return section_text if section_text else None
    
    def _clean_section_text(self, text: str) -> str:
        """
        Clean section text by removing metadata artifacts only.
        Feature code heading lines (e.g. "(#0010) Feature name") are intentionally
        KEPT — stripping them orphaned the body text that follows, making the
        retrieved chunk unreadable without its heading context.
        """
        # Remove pagination artifacts like "Description (Part 181/922)"
        text = re.sub(r'\(Part\s+\d+/\d+\)', '', text)

        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()
    
    def _split_by_subheadings(self, text: str, section_name: str) -> List[tuple]:
        """Split section by H3 subheadings"""
        sub_chunks = []
        
        # Pattern for subheadings (capitalized phrases)
        lines = text.split('\n')
        current_subheading = None
        current_text = []
        
        for line in lines:
            # Check if this looks like a subheading
            if re.match(r'^[A-Z][a-z][a-z\s]+$', line.strip()) and len(line.strip()) < 50:
                # Save previous subsection
                if current_subheading:
                    sub_chunks.append((current_subheading, '\n'.join(current_text).strip()))
                
                # Start new subsection
                current_subheading = line.strip()
                current_text = []
            else:
                current_text.append(line)
        
        # Save last subsection
        if current_subheading:
            sub_chunks.append((current_subheading, '\n'.join(current_text).strip()))
        
        return sub_chunks if sub_chunks else [(section_name, text)]
    
    def _create_chunk(self, title: str, text: str, server_name: str, mtm: str, url: str,
                     priority: str = 'medium', strategy: str = 'generic', **extra_metadata) -> Dict:
        """Create a standardized chunk dictionary"""
        return {
            'text': f"{title}\n\n{text}",
            'metadata': {
                'section_type': 'content_section',
                'section_title': title,
                'server_name': server_name,
                'mtm': mtm,
                'source': url,
                'priority': priority,
                'query_type': 'full_rag',  # Requires LLM
                'chunk_strategy': strategy,
                **extra_metadata
            }
        }


# Made with Bob