"""
Query Classifier for Hybrid RAG System
Routes queries to appropriate handlers: table lookup, metadata lookup, or full RAG
"""

import re
import logging
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries that can be handled"""
    TABLE_LOOKUP = "table_lookup"
    METADATA_LOOKUP = "metadata_lookup"
    RAG = "rag"


class QueryClassifier:
    """Classify queries to route to appropriate handler"""
    
    # Patterns for lifecycle/table queries
    LIFECYCLE_PATTERNS = [
        r"when\s+(?:was|is|will)\s+.*(?:announced|available|withdrawn|discontinued)",
        r"(?:announcement|availability|withdrawal|discontinuation)\s+date",
        r"what\s+(?:is|was)\s+the\s+(?:announcement|availability|withdrawal)\s+date",
        r"when\s+(?:did|does|will)\s+.*(?:announce|become\s+available|withdraw)",
    ]
    
    # Patterns for feature availability queries
    FEATURE_PATTERNS = [
        r"is\s+(?:feature\s+)?(?:code\s+)?[A-Z0-9]{4}\s+(?:still\s+)?available",
        r"can\s+(?:i|we)\s+(?:still\s+)?order\s+(?:feature\s+)?(?:code\s+)?[A-Z0-9]{4}",
        r"(?:feature\s+)?(?:code\s+)?[A-Z0-9]{4}\s+(?:withdrawal|discontinued)",
        r"when\s+(?:was|is)\s+(?:feature\s+)?(?:code\s+)?[A-Z0-9]{4}\s+withdrawn",
    ]
    
    # Server model patterns
    SERVER_PATTERNS = [
        r"(?:IBM\s+)?Power\s+(?:System\s+)?[ELS]\d{3,4}",
        r"(?:IBM\s+)?Power\s+(?:System\s+)?[HL]C?\d{3,4}",
        r"(?:IBM\s+)?Power\s+(?:System\s+)?IC\d{3,4}",
        r"\d{4}-[A-Z0-9]{3}",  # MTM format
    ]
    
    def __init__(self):
        """Initialize classifier with compiled patterns"""
        self.lifecycle_regex = [re.compile(p, re.IGNORECASE) for p in self.LIFECYCLE_PATTERNS]
        self.feature_regex = [re.compile(p, re.IGNORECASE) for p in self.FEATURE_PATTERNS]
        self.server_regex = [re.compile(p, re.IGNORECASE) for p in self.SERVER_PATTERNS]
    
    def classify(self, query: str) -> QueryType:
        """
        Classify query type
        
        Args:
            query: User query string
            
        Returns:
            QueryType enum value
        """
        query_lower = query.lower()
        
        # Check for lifecycle/table queries
        if self._is_lifecycle_query(query):
            logger.info(f"Classified as TABLE_LOOKUP: {query[:50]}...")
            return QueryType.TABLE_LOOKUP
        
        # Check for feature availability queries
        if self._is_feature_query(query):
            logger.info(f"Classified as METADATA_LOOKUP: {query[:50]}...")
            return QueryType.METADATA_LOOKUP
        
        # Default to full RAG
        logger.info(f"Classified as RAG: {query[:50]}...")
        return QueryType.RAG
    
    def _is_lifecycle_query(self, query: str) -> bool:
        """Check if query is about product lifecycle dates"""
        # Must match lifecycle pattern AND mention a server
        has_lifecycle = any(regex.search(query) for regex in self.lifecycle_regex)
        has_server = any(regex.search(query) for regex in self.server_regex)
        
        return has_lifecycle and has_server
    
    def _is_feature_query(self, query: str) -> bool:
        """Check if query is about feature availability"""
        return any(regex.search(query) for regex in self.feature_regex)
    
    def extract_server_model(self, query: str) -> Optional[str]:
        """
        Extract server model from query
        
        Args:
            query: User query string
            
        Returns:
            Server model string (e.g., "E1180") or None
        """
        for regex in self.server_regex:
            match = regex.search(query)
            if match:
                model = match.group(0)
                # Normalize to just the model number
                model = re.sub(r'(?:IBM\s+)?Power\s+(?:System\s+)?', '', model, flags=re.IGNORECASE)
                logger.info(f"Extracted server model: {model}")
                return model.strip()
        
        return None
    
    def extract_feature_code(self, query: str) -> Optional[str]:
        """
        Extract feature code from query
        
        Args:
            query: User query string
            
        Returns:
            Feature code (e.g., "EFA1") or None
        """
        # Look for 4-character alphanumeric codes
        match = re.search(r'\b([A-Z0-9]{4})\b', query, re.IGNORECASE)
        if match:
            code = match.group(1).upper()
            logger.info(f"Extracted feature code: {code}")
            return code
        
        return None
    
    def get_query_intent(self, query: str) -> Dict[str, any]:  # type: ignore
        """
        Extract full query intent including type and entities
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with query_type, server_model, feature_code, etc.
        """
        query_type = self.classify(query)
        
        intent = {
            'query_type': query_type.value,
            'original_query': query,
            'server_model': None,
            'feature_code': None,
            'lifecycle_field': None
        }
        
        if query_type == QueryType.TABLE_LOOKUP:
            intent['server_model'] = self.extract_server_model(query)
            intent['lifecycle_field'] = self._extract_lifecycle_field(query)
        
        elif query_type == QueryType.METADATA_LOOKUP:
            intent['feature_code'] = self.extract_feature_code(query)
        
        return intent
    
    def _extract_lifecycle_field(self, query: str) -> Optional[str]:
        """
        Determine which lifecycle field is being asked about
        
        Returns:
            'announced', 'available', 'withdrawn', or 'discontinued'
        """
        query_lower = query.lower()
        
        if 'announce' in query_lower:
            return 'announced'
        elif 'available' in query_lower or 'availability' in query_lower:
            return 'available'
        elif 'withdraw' in query_lower or 'withdrawal' in query_lower:
            return 'withdrawn'
        elif 'discontinue' in query_lower or 'discontinuation' in query_lower:
            return 'discontinued'
        
        return None


# Convenience function for quick classification
def classify_query(query: str) -> QueryType:
    """Quick classification without creating classifier instance"""
    classifier = QueryClassifier()
    return classifier.classify(query)


# Made with Bob