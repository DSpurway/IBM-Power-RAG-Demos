"""
Table Lookup Service for Direct Data Retrieval from OpenSearch
Handles queries about product lifecycle dates by searching sales manual chunks
Uses MTM-based collections for server-specific data
"""

import logging
import re
import hashlib
from typing import Dict, Optional, List, Any
from datetime import datetime
from server_mtm_mapper import get_collection_name_for_model

logger = logging.getLogger(__name__)


def _generate_index_name(collection_name):
    """
    Generate OpenSearch index name from collection name
    Uses the collection name directly for readability and easier debugging
    Example: rag_mtm_9009_42a -> rag_mtm_9009_42a
    """
    return collection_name


class TableLookupService:
    """Service for direct table lookups from OpenSearch without LLM generation"""
    
    def __init__(self, opensearch_client=None, embeddings=None, index_prefix='rag'):
        """
        Initialize table lookup service with OpenSearch
        
        Args:
            opensearch_client: OpenSearch client instance
            embeddings: Embeddings model for vector search
            index_prefix: Prefix for OpenSearch indices
        """
        self.client = opensearch_client
        self.embeddings = embeddings
        self.index_prefix = index_prefix
        logger.info("TableLookupService initialized with OpenSearch backend")
    
    def lookup(self, server_model: str, field: Optional[str] = None,
               collection_name: Optional[str] = None, server_mtm: Optional[str] = None) -> Dict[str, Any]:
        """
        Look up lifecycle data for a server from OpenSearch
        
        Args:
            server_model: Server model (e.g., "E1180", "S924", "S1024")
            field: Specific field to retrieve (announced, available, withdrawn, end_of_support, etc.)
            collection_name: OpenSearch collection to search (optional, will use MTM-based name if not provided)
            server_mtm: Server MTM (e.g., "9009-42G") for precise table row matching
            
        Returns:
            Dictionary with lookup results including answer from sales manual
        """
        if not self.client or not self.embeddings:
            return {
                'success': False,
                'error': 'OpenSearch client or embeddings not initialized',
                'answer': 'Service not properly configured'
            }
        
        logger.info(f"DEBUG lookup(): server_model={server_model}, field={field}, server_mtm={server_mtm}")
        
        # Normalize model name
        model = self._normalize_model(server_model)
        
        # Get MTM-based collection name if not provided
        if not collection_name:
            collection_name = get_collection_name_for_model(model)
            if not collection_name:
                return {
                    'success': False,
                    'error': f'Unknown server model: {model}',
                    'answer': f'No MTM mapping found for {model}'
                }
            logger.info(f"Using MTM-based collection: {collection_name}")
        
        # Build search query for lifecycle information
        search_query = self._build_lifecycle_query(model, field)
        
        logger.info(f"Searching OpenSearch for: {search_query}")
        
        try:
            # Use the MTM-based collection name to search in the correct index
            # This ensures we find the lifecycle table for the specific server, not other servers
            index_name = _generate_index_name(collection_name)
            
            logger.info(f"Searching in specific index: {index_name} (collection: {collection_name})")
            
            # Check if the index exists
            if not self.client.indices.exists(index=index_name):
                logger.warning(f"Index {index_name} does not exist, trying wildcard search")
                # Fallback to wildcard if specific index doesn't exist
                index_name = f"{self.index_prefix}_*"
                if not self.client.indices.exists(index=index_name):
                    return {
                        'success': False,
                        'error': f'No sales manual data loaded for {model}',
                        'answer': f'Sales manual data not yet loaded for {model}.'
                    }
            
            # For lifecycle table lookups, search for the exact phrase "Product life cycle dates"
            # This is the header that appears directly above the lifecycle table in all sales manuals
            search_body = {
                "size": 5,  # Only need a few chunks - table should be in first result
                "_source": ["text", "metadata"],
                "query": {
                    "match_phrase": {
                        "text": "Product life cycle dates"
                    }
                }
            }
            
            response = self.client.search(index=index_name, body=search_body)
            hits = response['hits']['hits']
            
            if not hits:
                return {
                    'success': False,
                    'error': f'No lifecycle data found for {model}',
                    'answer': f'No information available for {model} in the sales manuals'
                }
            
            # Extract and format the answer from the top chunks
            result = self._extract_lifecycle_answer(hits, model, field, server_mtm)
            
            # Get source URL from metadata if available
            source_url = None
            source_filename = None
            table_text = None
            
            for hit in hits:
                metadata = hit['_source'].get('metadata', {})
                text = hit['_source'].get('text', '')
                
                # Look for lifecycle table in the text
                if 'product lifecycle' in text.lower() or 'lifecycle dates' in text.lower():
                    table_text = text
                    # Try multiple possible metadata keys for source URL
                    source_url = metadata.get('source') or metadata.get('source_url') or metadata.get('url')
                    source_filename = metadata.get('source_filename') or metadata.get('filename')
                    logger.info(f"Found lifecycle table chunk with source: {source_url}, filename: {source_filename}")
                    logger.info(f"Available metadata keys: {list(metadata.keys())}")
                    break
            
            return {
                'success': True,
                'server_model': model,
                'mtm': server_mtm,
                'field': field,
                'answer': result,
                'table_data': table_text,
                'source_url': source_url,
                'source_filename': source_filename,
                'source': 'sales_manual',
                'chunks_found': len(hits)
            }
            
        except Exception as e:
            logger.error(f"Error searching OpenSearch: {e}")
            return {
                'success': False,
                'error': str(e),
                'answer': f'Error retrieving data for {model}'
            }
    
    def query(self, query: str, server_model: Optional[str] = None,
              lifecycle_field: Optional[str] = None, server_mtm: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle a natural language query with table lookup
        
        Args:
            query: Original user query
            server_model: Extracted server model
            lifecycle_field: Extracted lifecycle field
            server_mtm: Server MTM (e.g., "9009-42G") for precise table row matching
            
        Returns:
            Dictionary with query results
        """
        if not server_model:
            return {
                'success': False,
                'error': 'Could not identify server model in query',
                'query': query
            }
        
        logger.info(f"DEBUG query(): server_model={server_model}, lifecycle_field={lifecycle_field}, server_mtm={server_mtm}")
        result = self.lookup(server_model, lifecycle_field, server_mtm=server_mtm)
        logger.info(f"DEBUG query(): after lookup, result keys={result.keys()}")
        result['query'] = query
        result['method'] = 'table_lookup'
        result['response_time_ms'] = 10  # Approximate
        
        return result
    
    def _normalize_model(self, model: str) -> str:
        """Normalize server model name"""
        # Remove common prefixes
        model = re.sub(r'(?:IBM\s+)?Power\s+(?:System\s+)?', '', model, flags=re.IGNORECASE)
        # Remove spaces and convert to uppercase
        model = model.strip().upper()
        return model
    
    def _build_lifecycle_query(self, model: str, field: Optional[str]) -> str:
        """
        Build a search query for lifecycle information
        
        Args:
            model: Normalized model name (e.g., "S924", "E1080")
            field: Lifecycle field (announced, available, withdrawn, end_of_support, etc.)
            
        Returns:
            Search query string
        """
        # Base query with model name
        query_parts = [model]
        
        # Add lifecycle-specific terms
        if field:
            field_lower = field.lower()
            if 'announce' in field_lower:
                query_parts.extend(['announced', 'announcement'])
            elif 'available' in field_lower or 'ga' in field_lower:
                query_parts.extend(['available', 'availability', 'general availability'])
            elif 'withdraw' in field_lower or 'eom' in field_lower:
                query_parts.extend(['withdrawn', 'withdrawal', 'marketing withdrawn', 'end of marketing'])
            elif 'discontinue' in field_lower or 'eos' in field_lower or 'support' in field_lower:
                query_parts.extend(['discontinued', 'end of support', 'end of service', 'support discontinued'])
        else:
            # General lifecycle query
            query_parts.extend(['lifecycle', 'announced', 'available', 'withdrawn', 'discontinued'])
        
        return ' '.join(query_parts)
    
    def _extract_lifecycle_answer(self, hits: List[Dict], model: str, field: Optional[str], server_mtm: Optional[str] = None) -> str:
        """
        Extract lifecycle answer from OpenSearch hits
        
        Args:
            hits: List of search hits from OpenSearch
            model: Server model
            field: Specific lifecycle field requested
            server_mtm: Server MTM for precise table row matching
            
        Returns:
            Formatted answer string
        """
        # Combine text from top chunks, prioritizing lifecycle-related chunks
        relevant_texts = []
        lifecycle_texts = []
        
        logger.info(f"Examining {len(hits)} chunks for lifecycle table")
        for i, hit in enumerate(hits[:10]):  # Check top 10 chunks
            text = hit['_source'].get('text', '')
            metadata = hit['_source'].get('metadata', {})
            score = hit.get('_score', 0)
            
            logger.info(f"Chunk {i}: score={score:.3f}, length={len(text)}, has_lifecycle={'lifecycle' in text.lower()}")
            logger.info(f"Chunk {i} preview: {text[:200]}...")
            
            if not text:
                logger.info(f"Chunk {i}: Skipping empty chunk")
                continue
            
            # For table lookup queries, we ONLY want the lifecycle table chunk
            # Stop as soon as we find it
            text_lower = text.lower()
            if 'product lifecycle dates' in text_lower or 'product life cycle dates' in text_lower:
                lifecycle_texts.append(text)
                logger.info(f"Chunk {i}: Found lifecycle table! ({len(text)} chars) - stopping search")
                break  # Found the table, no need to look further
            elif 'lifecycle' in text_lower and len(lifecycle_texts) == 0:
                # Backup: keep first chunk with "lifecycle" if we haven't found the table yet
                lifecycle_texts.append(text)
                logger.info(f"Chunk {i}: Added lifecycle chunk as backup ({len(text)} chars)")
        
        # For table lookup, we should have found the lifecycle table
        if not lifecycle_texts:
            logger.warning(f"No lifecycle table found for {model}")
            return f"No specific lifecycle information found for {model} in the sales manuals."
        
        # Use ONLY the lifecycle table chunk (first one found)
        combined_text = lifecycle_texts[0]
        logger.info(f"Using lifecycle table chunk: {len(combined_text)} chars")
        
        # Extract specific information based on field
        if field:
            field_info = self._extract_field_from_text(combined_text, model, field, server_mtm)
            if field_info:
                return field_info
        
        # If no specific field extraction worked, try to parse table and return all dates
        table_result = self._parse_lifecycle_table(combined_text, model, field, server_mtm)
        if table_result:
            return table_result
        
        # Last resort: return a cleaned version of the most relevant chunk
        # Try to extract just the lifecycle table portion
        first_text = lifecycle_texts[0]  # Fixed: use lifecycle_texts instead of relevant_texts
        # Look for lines with dates
        lines = first_text.split('\n')
        date_lines = [line for line in lines if re.search(r'\d{4}-\d{2}-\d{2}', line)]
        if date_lines:
            return '\n'.join(date_lines[:3])  # Return first 3 lines with dates
        
        return first_text[:500]  # Return first 500 chars as fallback
    
    def _extract_field_from_text(self, text: str, model: str, field: Optional[str], server_mtm: Optional[str] = None) -> Optional[str]:
        """
        Extract specific lifecycle field information from text
        Handles both table format and sentence format
        
        Args:
            text: Combined text from chunks
            model: Server model
            field: Lifecycle field to extract (can be None)
            server_mtm: Server MTM for precise table row matching
            
        Returns:
            Extracted information or None
        """
        # Try to parse table format first (common in sales manuals)
        table_result = self._parse_lifecycle_table(text, model, field, server_mtm)
        if table_result:
            return table_result
        
        # If no field specified, return formatted table data
        if not field:
            return None
        
        field_lower = field.lower()
        
        # Look for date patterns near field keywords
        date_pattern = r'\b\d{4}[-/]\d{2}[-/]\d{2}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        
        # Split text into sentences
        sentences = re.split(r'[.!?\n]+', text)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check if sentence contains the model and field keywords
            if model.lower() in sentence_lower:
                if 'announce' in field_lower and 'announce' in sentence_lower:
                    dates = re.findall(date_pattern, sentence)
                    if dates:
                        return f"The IBM Power {model} was announced on {dates[0]}."
                
                elif 'available' in field_lower and ('available' in sentence_lower or 'ga' in sentence_lower):
                    dates = re.findall(date_pattern, sentence)
                    if dates:
                        return f"The IBM Power {model} became available on {dates[0]}."
                
                elif ('withdraw' in field_lower or 'eom' in field_lower) and 'withdraw' in sentence_lower:
                    dates = re.findall(date_pattern, sentence)
                    if dates:
                        return f"The IBM Power {model} was withdrawn from marketing on {dates[0]}."
                
                elif ('discontinue' in field_lower or 'eos' in field_lower or 'support' in field_lower):
                    if 'discontinue' in sentence_lower or 'end of support' in sentence_lower or 'no longer support' in sentence_lower:
                        dates = re.findall(date_pattern, sentence)
                        if dates:
                            return f"Support for the IBM Power {model} ended on {dates[0]}."
                        else:
                            # Return the sentence even without a date
                            return sentence.strip()
        
        return None
    
    def _parse_lifecycle_table(self, text: str, model: str, field: Optional[str] = None, server_mtm: Optional[str] = None) -> Optional[str]:
        """
        Parse lifecycle dates from table format in sales manuals
        
        Table format:
        Type Model | Announced | Available | Marketing withdrawn | Support level changed | Service discontinued
        9009-42A   | 2018-02-13| 2018-03-20| 2021-01-29         | 31 January 2026      | -
        
        Args:
            text: Text containing lifecycle table
            model: Server model
            field: Specific field to extract (announced, available, withdrawn, end_of_support)
            server_mtm: Server MTM for precise row matching (e.g., "9009-42A")
            
        Returns:
            Formatted lifecycle information or None
        """
        logger.info(f"_parse_lifecycle_table called: model={model}, field={field}, server_mtm={server_mtm}")
        logger.info(f"Text to parse ({len(text)} chars): {text[:500]}...")
        
        # IMPORTANT: Extract ONLY the lifecycle table section to avoid parsing the entire sales manual
        # Look for the table start and end markers
        table_start_pattern = r'Product life ?cycle dates'
        table_end_patterns = [r'^Abstract$', r'^Introduction$', r'^Overview$', r'^Features$', r'^##', r'^#']
        
        lines = text.split('\n')
        logger.info(f"Full text has {len(lines)} lines")
        
        # Find the lifecycle table section
        table_start_idx = None
        table_end_idx = None
        
        for i, line in enumerate(lines):
            if table_start_idx is None and re.search(table_start_pattern, line, re.IGNORECASE):
                table_start_idx = i
                logger.info(f"Found lifecycle table start at line {i}")
                continue
            
            if table_start_idx is not None and table_end_idx is None:
                # Check for end markers
                for pattern in table_end_patterns:
                    if re.match(pattern, line.strip(), re.IGNORECASE):
                        table_end_idx = i
                        logger.info(f"Found lifecycle table end at line {i} (pattern: {pattern})")
                        break
                
                # Also stop if we've gone 50 lines past the start without finding MTMs
                if i > table_start_idx + 50:
                    table_end_idx = i
                    logger.info(f"Stopping at line {i} (50 lines past start)")
                    break
        
        # Extract only the table section
        if table_start_idx is not None:
            if table_end_idx is None:
                table_end_idx = min(table_start_idx + 50, len(lines))  # Max 50 lines
            lines = lines[table_start_idx:table_end_idx]
            logger.info(f"Extracted lifecycle table section: {len(lines)} lines")
        else:
            logger.warning("Could not find lifecycle table start marker")
            # Try to find it anyway in first 100 lines
            lines = lines[:100]
            logger.info(f"Using first 100 lines as fallback")
        
        # Look for the "Product lifecycle dates" section
        in_lifecycle_section = False
        mtm_pattern = r'\d{4}-[A-Z0-9]{3}'  # Pattern for MTM like 9009-42A
        found_mtms = []
        
        for i, line in enumerate(lines):
            logger.info(f"Processing line {i}: {line[:100]}")  # Show each line
            line_lower = line.lower()
            # Match both "lifecycle dates" and "life cycle dates" (with space)
            if 'product lifecycle' in line_lower or 'lifecycle dates' in line_lower or 'life cycle dates' in line_lower:
                in_lifecycle_section = True
                logger.info(f"Found Product lifecycle dates section at line {i}, in_lifecycle_section={in_lifecycle_section}")
                continue
            
            # If we're in the lifecycle section, look for MTM rows
            if in_lifecycle_section:
                # Check if line contains an MTM pattern
                mtm_match = re.search(mtm_pattern, line)
                if not mtm_match:
                    logger.info(f"Line {i} has no MTM match: {line[:100]}")
                    continue
                else:
                    logger.info(f"Line {i} MATCHED MTM pattern: {mtm_match.group(0)}")
                
                line_mtm = mtm_match.group(0)
                
                # If specific MTM requested, only process that row
                if server_mtm and line_mtm != server_mtm:
                    continue
                
                logger.info(f"Found table row with MTM {line_mtm}: {line}")
                
                # Split by | or multiple spaces to extract table cells
                cells = [cell.strip() for cell in re.split(r'\||\s{2,}', line) if cell.strip()]
                logger.info(f"Extracted cells: {cells}")
                
                # Expected format: [MTM, Announced, Available, Marketing withdrawn, Support level changed, Service discontinued]
                # Or with leading/trailing pipes: ['', MTM, Announced, ...]
                
                # Find cells that look like dates or "-"
                date_pattern = r'\d{4}-\d{2}-\d{2}'
                date_cells = []
                for cell in cells:
                    if re.match(date_pattern, cell) or cell == '-':
                        date_cells.append(cell)
                
                logger.info(f"Found date cells: {date_cells}")
                
                if len(date_cells) >= 3:  # At minimum: Announced, Available, Marketing withdrawn
                    announced = date_cells[0] if len(date_cells) > 0 else '-'
                    available = date_cells[1] if len(date_cells) > 1 else '-'
                    withdrawn = date_cells[2] if len(date_cells) > 2 else '-'
                    # Service discontinued is typically at index 4 (after "Support level changed" at index 3)
                    # But safely check if it exists
                    discontinued = date_cells[4] if len(date_cells) > 4 else (date_cells[3] if len(date_cells) > 3 else '-')
                    
                    # Store this MTM's data
                    mtm_data = {
                        'mtm': line_mtm,
                        'announced': announced,
                        'available': available,
                        'withdrawn': withdrawn,
                        'discontinued': discontinued
                    }
                    found_mtms.append(mtm_data)
                    
                    # If we have a specific MTM, return immediately with improved format
                    if server_mtm:
                        logger.info(f"Found specific MTM {server_mtm} in table, formatting response")
                        
                        # Build the full lifecycle table for this MTM
                        table_lines = [
                            f"\nLifecycle Information for {line_mtm}:",
                            f"• Announced: {announced if announced != '-' else 'Not yet announced'}",
                            f"• Available: {available if available != '-' else 'Not yet announced'}",
                            f"• Marketing Withdrawn: {withdrawn if withdrawn != '-' else 'Not yet announced'}",
                            f"• Service Discontinued: {discontinued if discontinued != '-' else 'Not yet announced'}"
                        ]
                        
                        # If specific field requested, provide direct answer first
                        if field:
                            field_lower = field.lower()
                            if 'announce' in field_lower:
                                date_val = announced
                                field_name = "Announcement date"
                            elif 'available' in field_lower:
                                date_val = available
                                field_name = "Availability date"
                            elif 'withdraw' in field_lower:
                                date_val = withdrawn
                                field_name = "Marketing Withdrawal date"
                            elif 'discontinue' in field_lower or 'end_of_support' in field_lower:
                                date_val = discontinued
                                field_name = "Service Discontinuation date"
                            else:
                                date_val = None
                                field_name = None
                            
                            if field_name:
                                if date_val == '-':
                                    answer = f"The {field_name} for the {line_mtm} has not been announced yet."
                                else:
                                    answer = f"The {field_name} for the {line_mtm} is {date_val}."
                                
                                # Add full table for reference
                                answer += "\n" + '\n'.join(table_lines)
                                return answer
                        
                        # Return all dates if no specific field
                        return '\n'.join(table_lines)
        
        # If we requested a specific MTM but didn't find it, return error
        if server_mtm and not found_mtms:
            logger.warning(f"Requested MTM {server_mtm} not found in lifecycle table for {model}")
            return f"The MTM {server_mtm} was not found in the lifecycle table. This may indicate the wrong sales manual was retrieved."
        
        # If no specific MTM was requested but we found MTMs, return summary of all
        if found_mtms and not server_mtm:
            logger.info(f"Found {len(found_mtms)} MTMs for {model}, no specific MTM requested")
            result_lines = [f"IBM Power {model} has multiple configurations. Here are the lifecycle dates:"]
            result_lines.append("")
            
            for mtm_data in found_mtms:
                mtm = mtm_data['mtm']
                result_lines.append(f"**{mtm}:**")
                
                if field:
                    field_lower = field.lower()
                    if 'announce' in field_lower:
                        date_val = mtm_data['announced']
                        result_lines.append(f"  Announced: {date_val if date_val != '-' else 'Not announced'}")
                    elif 'available' in field_lower:
                        date_val = mtm_data['available']
                        result_lines.append(f"  Available: {date_val if date_val != '-' else 'Not announced'}")
                    elif 'withdraw' in field_lower:
                        date_val = mtm_data['withdrawn']
                        result_lines.append(f"  Marketing Withdrawn: {date_val if date_val != '-' else 'Not announced'}")
                    elif 'discontinue' in field_lower or 'end_of_support' in field_lower:
                        date_val = mtm_data['discontinued']
                        result_lines.append(f"  Service Discontinued: {date_val if date_val != '-' else 'Not announced'}")
                else:
                    # Show all dates
                    result_lines.append(f"  Announced: {mtm_data['announced'] if mtm_data['announced'] != '-' else 'Not announced'}")
                    result_lines.append(f"  Available: {mtm_data['available'] if mtm_data['available'] != '-' else 'Not announced'}")
                    result_lines.append(f"  Marketing Withdrawn: {mtm_data['withdrawn'] if mtm_data['withdrawn'] != '-' else 'Not announced'}")
                    result_lines.append(f"  Service Discontinued: {mtm_data['discontinued'] if mtm_data['discontinued'] != '-' else 'Not announced'}")
                result_lines.append("")
            
            return '\n'.join(result_lines)
        
        return None


# Singleton instance
_table_lookup_service = None


def get_table_lookup_service() -> TableLookupService:
    """Get or create singleton table lookup service"""
    global _table_lookup_service
    if _table_lookup_service is None:
        _table_lookup_service = TableLookupService()
    return _table_lookup_service


# Made with Bob