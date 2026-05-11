"""
Smart Hierarchical Chunker for IBM Sales Manuals
Preserves table structure for direct lookup and creates semantic chunks for RAG
"""

import re
import logging
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class SalesManualChunker:
    """
    Intelligent chunker for IBM Power Sales Manual pages
    Preserves table structure and creates semantically meaningful chunks
    """
    
    def __init__(self, max_chunk_size=1500, overlap=100):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk_sales_manual(self, full_text: str, server_name: str, mtm: str, url: str) -> List[Dict[str, Any]]:
        """
        Main chunking method - processes entire Sales Manual
        
        Args:
            full_text: Complete scraped text from Sales Manual page
            server_name: Server name (e.g., "IBM Power System S924")
            mtm: Machine Type-Model (e.g., "9009-42A")
            url: Source URL
            
        Returns:
            List of chunks with text and metadata
        """
        chunks = []
        
        # 1. Extract and preserve lifecycle table (CRITICAL for direct lookup)
        lifecycle_chunk = self._extract_lifecycle_table(full_text, server_name, mtm, url)
        if lifecycle_chunk:
            chunks.append(lifecycle_chunk)
            logger.info(f"✓ Extracted lifecycle table for {mtm}")
        
        # 2. Extract feature codes with metadata (for metadata search)
        feature_chunks = self._extract_feature_codes(full_text, server_name, mtm, url)
        chunks.extend(feature_chunks)
        logger.info(f"✓ Extracted {len(feature_chunks)} feature codes for {mtm}")
        
        # 3. Extract other sections for RAG
        section_chunks = self._extract_sections(full_text, server_name, mtm, url)
        chunks.extend(section_chunks)
        logger.info(f"✓ Extracted {len(section_chunks)} section chunks for {mtm}")
        
        logger.info(f"Total chunks created for {mtm}: {len(chunks)}")
        return chunks
    
    def _extract_lifecycle_table(self, text: str, server_name: str, mtm: str, url: str) -> Optional[Dict]:
        """
        Extract lifecycle table and preserve as Markdown for direct parsing
        This enables fast, accurate responses without LLM
        """
        # Look for "Product lifecycle dates" or "Product life cycle dates"
        table_pattern = r'Product\s+life\s*cycle\s+dates\s*\n+(.*?)(?=\n\n[A-Z]|\Z)'
        match = re.search(table_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if not match:
            logger.warning(f"No lifecycle table found for {mtm}")
            return None
        
        table_text = match.group(0).strip()
        
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
                'chunk_strategy': 'preserve_table_structure'
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
    
    def _extract_feature_codes(self, text: str, server_name: str, mtm: str, url: str) -> List[Dict]:
        """
        Extract individual feature codes with metadata
        Enables metadata-based search and filtering
        """
        chunks = []
        
        # Pattern for feature codes: (#XXXX) Feature Name
        # Followed by optional withdrawal date and details
        feature_pattern = r'\(#([A-Z0-9]{4})\)\s+([^\n]+)\n((?:.*?\n)*?)(?=\(#[A-Z0-9]{4}\)|\n\n[A-Z][a-z]+\s*\n|\Z)'
        
        for match in re.finditer(feature_pattern, text, re.DOTALL):
            feature_code = match.group(1)
            feature_name = match.group(2).strip()
            feature_details = match.group(3).strip()
            
            # Extract structured metadata
            metadata = self._parse_feature_metadata(feature_details)
            
            # Build chunk text
            chunk_text = f"Feature Code: #{feature_code}\n"
            chunk_text += f"Name: {feature_name}\n\n"
            chunk_text += feature_details
            
            chunks.append({
                'text': chunk_text,
                'metadata': {
                    'section_type': 'feature_code',
                    'section_title': 'Features',
                    'feature_code': feature_code,
                    'feature_name': feature_name,
                    'server_name': server_name,
                    'mtm': mtm,
                    'source': url,
                    'priority': 'high',
                    'query_type': 'metadata_search',  # Can use metadata filtering
                    'chunk_strategy': 'per_feature_code',
                    **metadata  # Add parsed metadata (withdrawal_date, csu, etc.)
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
    
    def _extract_sections(self, text: str, server_name: str, mtm: str, url: str) -> List[Dict]:
        """
        Extract other sections for RAG queries
        These require LLM for synthesis and complex queries
        """
        chunks = []
        
        # Define section patterns and chunking strategies
        sections_config = {
            'Abstract': {'strategy': 'keep_intact', 'priority': 'high'},
            'Highlights': {'strategy': 'split_if_large', 'priority': 'medium'},
            'Description': {'strategy': 'split_by_paragraph', 'priority': 'medium'},
            'Product positioning': {'strategy': 'keep_intact', 'priority': 'medium'},
            'Models': {'strategy': 'keep_intact', 'priority': 'high'},
            'Technical description': {'strategy': 'split_by_subheading', 'priority': 'high'},
            'Accessories': {'strategy': 'keep_intact', 'priority': 'low'}
        }
        
        for section_name, config in sections_config.items():
            section_text = self._find_section(text, section_name)
            if not section_text:
                continue
            
            strategy = config['strategy']
            
            if strategy == 'keep_intact':
                chunks.append(self._create_chunk(
                    section_name, section_text, server_name, mtm, url,
                    priority=config['priority'], strategy='keep_intact'
                ))
            
            elif strategy == 'split_if_large':
                if len(section_text) > self.max_chunk_size:
                    sub_chunks = self.text_splitter.split_text(section_text)
                    for i, sub_chunk in enumerate(sub_chunks):
                        chunks.append(self._create_chunk(
                            f"{section_name} (Part {i+1}/{len(sub_chunks)})",
                            sub_chunk, server_name, mtm, url,
                            priority=config['priority'], strategy='split_large',
                            part_index=i, total_parts=len(sub_chunks)
                        ))
                else:
                    chunks.append(self._create_chunk(
                        section_name, section_text, server_name, mtm, url,
                        priority=config['priority'], strategy='keep_intact'
                    ))
            
            elif strategy == 'split_by_subheading':
                sub_chunks = self._split_by_subheadings(section_text, section_name)
                for sub_name, sub_text in sub_chunks:
                    chunks.append(self._create_chunk(
                        f"{section_name} - {sub_name}",
                        sub_text, server_name, mtm, url,
                        priority=config['priority'], strategy='subheading_split',
                        subsection=sub_name
                    ))
            
            elif strategy == 'split_by_paragraph':
                sub_chunks = self.text_splitter.split_text(section_text)
                for i, sub_chunk in enumerate(sub_chunks):
                    chunks.append(self._create_chunk(
                        f"{section_name} (Part {i+1}/{len(sub_chunks)})",
                        sub_chunk, server_name, mtm, url,
                        priority=config['priority'], strategy='paragraph_split',
                        part_index=i, total_parts=len(sub_chunks)
                    ))
        
        return chunks
    
    def _find_section(self, text: str, section_name: str) -> Optional[str]:
        """Find a section by name in the text"""
        # Pattern: Section name followed by content until next section
        pattern = rf'{re.escape(section_name)}\s*\n+(.*?)(?=\n\n[A-Z][a-z]+\s*\n|\Z)'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None
    
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