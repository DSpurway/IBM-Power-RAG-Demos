"""
Table Lookup Service for Direct Data Retrieval
Handles queries about product lifecycle dates from structured tables
"""

import logging
import re
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TableLookupService:
    """Service for direct table lookups without LLM"""
    
    # Product lifecycle table data
    # This will be populated from scraped data or can be maintained separately
    LIFECYCLE_DATA = {
        "E1180": {
            "model": "E1180",
            "full_name": "IBM Power E1180",
            "mtm": "9080-HEU",
            "announced": "2025-07-08",
            "available": "2025-07-25",
            "marketing_withdrawn": None,
            "service_discontinued": None,
        },
        "E1150": {
            "model": "E1150",
            "full_name": "IBM Power E1150",
            "mtm": "9043-MRU",
            "announced": "2024-10-08",
            "available": "2024-10-25",
            "marketing_withdrawn": None,
            "service_discontinued": None,
        },
        "E1080": {
            "model": "E1080",
            "full_name": "IBM Power E1080",
            "mtm": "9080-HEX",
            "announced": "2021-09-14",
            "available": "2021-09-17",
            "marketing_withdrawn": None,
            "service_discontinued": None,
        },
        "E1050": {
            "model": "E1050",
            "full_name": "IBM Power E1050",
            "mtm": "9043-MRX",
            "announced": "2023-03-07",
            "available": "2023-03-24",
            "marketing_withdrawn": None,
            "service_discontinued": None,
        },
        # Add more servers as they are scraped
    }
    
    def __init__(self):
        """Initialize table lookup service"""
        self.data = self.LIFECYCLE_DATA.copy()
        logger.info(f"TableLookupService initialized with {len(self.data)} servers")
    
    def lookup(self, server_model: str, field: Optional[str] = None) -> Dict[str, any]:  # type: ignore
        """
        Look up lifecycle data for a server
        
        Args:
            server_model: Server model (e.g., "E1180", "S1024")
            field: Specific field to retrieve (announced, available, etc.)
            
        Returns:
            Dictionary with lookup results
        """
        # Normalize model name
        model = self._normalize_model(server_model)
        
        if model not in self.data:
            return {
                'success': False,
                'error': f'Server model {server_model} not found in lifecycle data',
                'available_models': list(self.data.keys())
            }
        
        server_data = self.data[model]
        
        if field:
            # Return specific field
            field_value = server_data.get(field)
            return {
                'success': True,
                'server_model': model,
                'full_name': server_data['full_name'],
                'field': field,
                'value': field_value,
                'formatted_answer': self._format_answer(server_data, field, field_value)
            }
        else:
            # Return all lifecycle data
            return {
                'success': True,
                'server_model': model,
                'data': server_data,
                'formatted_answer': self._format_full_lifecycle(server_data)
            }
    
    def query(self, query: str, server_model: Optional[str] = None, 
              lifecycle_field: Optional[str] = None) -> Dict[str, any]:  # type: ignore
        """
        Handle a natural language query with table lookup
        
        Args:
            query: Original user query
            server_model: Extracted server model
            lifecycle_field: Extracted lifecycle field
            
        Returns:
            Dictionary with query results
        """
        if not server_model:
            return {
                'success': False,
                'error': 'Could not identify server model in query',
                'query': query
            }
        
        result = self.lookup(server_model, lifecycle_field)
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
    
    def _format_answer(self, server_data: Dict, field: str, value: any) -> str:  # type: ignore
        """Format a natural language answer"""
        full_name = server_data['full_name']
        
        if value is None:
            return f"The {field} date for {full_name} is not available or not applicable."
        
        # Format based on field type
        if field == 'announced':
            return f"The {full_name} was announced on {value}."
        elif field == 'available':
            return f"The {full_name} became available on {value}."
        elif field == 'marketing_withdrawn' or field == 'withdrawn':
            return f"The {full_name} was withdrawn from marketing on {value}."
        elif field == 'service_discontinued' or field == 'discontinued':
            return f"Service for the {full_name} was discontinued on {value}."
        else:
            return f"The {field} for {full_name} is {value}."
    
    def _format_full_lifecycle(self, server_data: Dict) -> str:
        """Format complete lifecycle information"""
        lines = [f"Product Lifecycle for {server_data['full_name']} ({server_data['mtm']}):"]
        
        if server_data.get('announced'):
            lines.append(f"- Announced: {server_data['announced']}")
        if server_data.get('available'):
            lines.append(f"- Available: {server_data['available']}")
        if server_data.get('marketing_withdrawn'):
            lines.append(f"- Marketing Withdrawn: {server_data['marketing_withdrawn']}")
        else:
            lines.append(f"- Marketing Withdrawn: Not withdrawn")
        if server_data.get('service_discontinued'):
            lines.append(f"- Service Discontinued: {server_data['service_discontinued']}")
        else:
            lines.append(f"- Service Discontinued: Still supported")
        
        return '\n'.join(lines)
    
    def update_lifecycle_data(self, model: str, data: Dict):
        """
        Update lifecycle data for a server
        
        Args:
            model: Server model
            data: Dictionary with lifecycle fields
        """
        model = self._normalize_model(model)
        
        if model not in self.data:
            self.data[model] = {
                'model': model,
                'full_name': data.get('full_name', f'IBM Power {model}'),
                'mtm': data.get('mtm', ''),
            }
        
        # Update fields
        for field in ['announced', 'available', 'marketing_withdrawn', 'service_discontinued']:
            if field in data:
                self.data[model][field] = data[field]
        
        logger.info(f"Updated lifecycle data for {model}")
    
    def load_from_metadata(self, metadata: Dict):
        """
        Load lifecycle data from scraped metadata
        
        Args:
            metadata: Metadata dictionary from web scraper
        """
        # Extract lifecycle table if present
        if 'lifecycle_table' in metadata:
            for row in metadata['lifecycle_table']:
                model = self._normalize_model(row.get('model', ''))
                if model:
                    self.update_lifecycle_data(model, row)
        
        logger.info(f"Loaded lifecycle data from metadata")
    
    def get_all_models(self) -> List[str]:
        """Get list of all available server models"""
        return list(self.data.keys())
    
    def search_models(self, query: str) -> List[str]:
        """
        Search for models matching a query
        
        Args:
            query: Search query
            
        Returns:
            List of matching model names
        """
        query_lower = query.lower()
        matches = []
        
        for model, data in self.data.items():
            if (query_lower in model.lower() or 
                query_lower in data['full_name'].lower() or
                query_lower in data.get('mtm', '').lower()):
                matches.append(model)
        
        return matches


# Singleton instance
_table_lookup_service = None


def get_table_lookup_service() -> TableLookupService:
    """Get or create singleton table lookup service"""
    global _table_lookup_service
    if _table_lookup_service is None:
        _table_lookup_service = TableLookupService()
    return _table_lookup_service


# Made with Bob