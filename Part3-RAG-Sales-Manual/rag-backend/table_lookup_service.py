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
               collection_name: str = None, server_mtm: Optional[str] = None) -> Dict[str, Any]:
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
            # (script_score with vectors doesn't work well with wildcard patterns)
            search_body = {
                "size": 10,  # Get top 10 chunks
                "_source": ["text", "metadata"],
                "query": {
                    "multi_match": {
                        "query": search_query,
                        "fields": ["text^2", "metadata.filename"],
                        "type": "best_fields",
                        "operator": "or"
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
            answer = self._extract_lifecycle_answer(hits, model, field, server_mtm)
            
            return {
                'success': True,
                'server_model': model,
                'field': field,
                'answer': answer,
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
        # Combine text from top chunks
        relevant_texts = []
        for hit in hits[:5]:  # Use top 5 chunks
            text = hit['_source'].get('text', '')
            if text and model.upper() in text.upper():
                relevant_texts.append(text)
        
        if not relevant_texts:
            return f"No specific lifecycle information found for {model} in the sales manuals."
        
        # Combine the texts
        combined_text = '\n\n'.join(relevant_texts)
        
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
        lines = text.split('\n')
        
        # Look for the "Product lifecycle dates" section
        in_lifecycle_section = False
        for i, line in enumerate(lines):
            if 'product lifecycle' in line.lower() or 'lifecycle dates' in line.lower():
                in_lifecycle_section = True
                logger.info("Found Product lifecycle dates section")
                continue
            
            # If we're in the lifecycle section and find the MTM
            if in_lifecycle_section and server_mtm and server_mtm in line:
                logger.info(f"Found table row with MTM {server_mtm}: {line}")
                
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
                    
                    mtm_suffix = f" ({server_mtm})" if server_mtm else ""
                    
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