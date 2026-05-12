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
            # Search across ALL rag_* indices since bulk ingestion may have used different collection names
            # This is more flexible and works regardless of the collection naming scheme used
            index_pattern = f"{self.index_prefix}_*"
            
            logger.info(f"Searching across all indices: {index_pattern} (model: {model})")
            
            # Check if any indices exist
            if not self.client.indices.exists(index=index_pattern):
                return {
                    'success': False,
                    'error': f'No sales manual data loaded yet',
                    'answer': f'Sales manual data not yet loaded. Please wait for bulk ingestion to complete.'
                }
            
            # Use text-only search when searching across multiple indices
            # For lifecycle queries, prioritize chunks with "Product life cycle dates" or "lifecycle"
            # This ensures we find the actual lifecycle table, not just mentions of dates
            search_body = {
                "size": 10,  # Get top 10 chunks
                "_source": ["text", "metadata"],
                "query": {
                    "bool": {
                        "should": [
                            # Highest priority: chunks with "Product life cycle dates" (the table header)
                            {
                                "match_phrase": {
                                    "text": {
                                        "query": "Product life cycle dates",
                                        "boost": 10.0
                                    }
                                }
                            },
                            # High priority: chunks with "lifecycle" keyword
                            {
                                "match": {
                                    "text": {
                                        "query": "lifecycle",
                                        "boost": 5.0
                                    }
                                }
                            },
                            # Medium priority: chunks with the MTM (if we have it)
                            {
                                "match": {
                                    "text": {
                                        "query": server_mtm if server_mtm else model,
                                        "boost": 3.0
                                    }
                                }
                            },
                            # Lower priority: general search terms
                            {
                                "multi_match": {
                                    "query": search_query,
                                    "fields": ["text", "metadata.filename"],
                                    "boost": 1.0
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            
            response = self.client.search(index=index_pattern, body=search_body)
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
                    source_url = metadata.get('source_url') or metadata.get('url')
                    source_filename = metadata.get('filename')
                    logger.info(f"Found lifecycle table chunk with source: {source_url}")
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
        
        result = self.lookup(server_model, lifecycle_field, server_mtm=server_mtm)
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
            field_info = self._extract_field_from_text(combined_text, model, field)
            if field_info:
                return field_info
        
        # If no specific field extraction worked, try to parse table and return all dates
        table_result = self._parse_lifecycle_table(combined_text, model, field, server_mtm)
        if table_result:
            return table_result
        
        # Last resort: return a cleaned version of the most relevant chunk
        # Try to extract just the lifecycle table portion
        first_text = relevant_texts[0]
        # Look for lines with dates
        lines = first_text.split('\n')
        date_lines = [line for line in lines if re.search(r'\d{4}-\d{2}-\d{2}', line)]
        if date_lines:
            return '\n'.join(date_lines[:3])  # Return first 3 lines with dates
        
        return first_text[:500]  # Return first 500 chars as fallback
    
    def _extract_field_from_text(self, text: str, model: str, field: Optional[str]) -> Optional[str]:
        """
        Extract specific lifecycle field information from text
        Handles both table format and sentence format
        
        Args:
            text: Combined text from chunks
            model: Server model
            field: Lifecycle field to extract (can be None)
            
        Returns:
            Extracted information or None
        """
        # Try to parse table format first (common in sales manuals)
        table_result = self._parse_lifecycle_table(text, model, field)
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
        
        lines = text.split('\n')
        logger.info(f"Split into {len(lines)} lines")
        
        # Look for the "Product lifecycle dates" section
        in_lifecycle_section = False
        mtm_pattern = r'\d{4}-[A-Z0-9]{3}'  # Pattern for MTM like 9009-42A
        found_mtms = []
        
        for i, line in enumerate(lines):
            if 'product lifecycle' in line.lower() or 'lifecycle dates' in line.lower():
                in_lifecycle_section = True
                logger.info(f"Found Product lifecycle dates section at line {i}")
                continue
            
            # If we're in the lifecycle section, look for MTM rows
            if in_lifecycle_section:
                # Check if line contains an MTM pattern
                mtm_match = re.search(mtm_pattern, line)
                if not mtm_match:
                    continue
                
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
                    discontinued = date_cells[4] if len(date_cells) > 4 else '-'  # Skip "Support level changed" at index 3
                    
                    # Store this MTM's data
                    mtm_data = {
                        'mtm': line_mtm,
                        'announced': announced,
                        'available': available,
                        'withdrawn': withdrawn,
                        'discontinued': discontinued
                    }
                    found_mtms.append(mtm_data)
                    
                    # If we have a specific MTM, return immediately
                    if server_mtm:
                        mtm_suffix = f" ({server_mtm})"
                        
                        # If specific field requested, return just that date
                        if field:
                            field_lower = field.lower()
                            if 'announce' in field_lower:
                                if announced == '-':
                                    return f"The announcement date for the IBM Power {model}{mtm_suffix} has not been announced yet."
                                return f"The IBM Power {model}{mtm_suffix} was announced on {announced}."
                            elif 'available' in field_lower:
                                if available == '-':
                                    return f"The availability date for the IBM Power {model}{mtm_suffix} has not been announced yet."
                                return f"The IBM Power {model}{mtm_suffix} became available on {available}."
                            elif 'withdraw' in field_lower:
                                if withdrawn == '-':
                                    return f"The marketing withdrawal date for the IBM Power {model}{mtm_suffix} has not been announced yet."
                                return f"The IBM Power {model}{mtm_suffix} was withdrawn from marketing on {withdrawn}."
                            elif 'discontinue' in field_lower or 'end_of_support' in field_lower:
                                if discontinued == '-':
                                    return f"The service discontinuation date for the IBM Power {model}{mtm_suffix} has not been announced yet."
                                return f"Support for the IBM Power {model}{mtm_suffix} will be discontinued on {discontinued}."
                        
                        # Return all dates if no specific field
                        result_lines = [f"IBM Power {model}{mtm_suffix} Lifecycle Dates:"]
                        result_lines.append(f"• Announced: {announced if announced != '-' else 'Not yet announced'}")
                        result_lines.append(f"• Available: {available if available != '-' else 'Not yet announced'}")
                        result_lines.append(f"• Marketing Withdrawn: {withdrawn if withdrawn != '-' else 'Not yet announced'}")
                        result_lines.append(f"• Service Discontinued: {discontinued if discontinued != '-' else 'Not yet announced'}")
                        return '\n'.join(result_lines)
        
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