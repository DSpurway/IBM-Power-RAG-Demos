"""
Query Classifier for Hybrid RAG System
Routes queries to appropriate handlers: table lookup, metadata lookup, or full RAG
Enhanced with Watson Assistant integration for superior NLP
"""

import re
import logging
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

# Optional Watson Assistant integration
try:
    from watson_assistant_service import get_watson_assistant_service
    WATSON_AVAILABLE = True
    logger.info("Watson Assistant integration available")
except ImportError:
    WATSON_AVAILABLE = False
    logger.info("Watson Assistant not available, using regex-based classification")


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
        r"when\s+(?:did|does|will)\s+.*stop\s+(?:supporting|selling)",
        r"when\s+(?:was|is)\s+.*(?:end\s+of\s+(?:life|support|service|marketing))",
        r"(?:end\s+of\s+(?:life|support|service|marketing))\s+date",
        r"stop\s+support(?:ing)?",  # Added: "stop supporting"
        r"end(?:ed)?\s+support",     # Added: "end support", "ended support"
        r"no\s+longer\s+support",    # Added: "no longer support"
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
        r"\d{4}-[A-Z0-9]{3}",  # MTM format like 9080-HEU
        r"\b[ELS]\d{3,4}\b",  # Standalone model like E1180, S1024, L922
        r"\b[HL]C?\d{3,4}\b",  # Standalone model like H922, LC922
        r"\bIC\d{3,4}\b",  # Standalone model like IC922
    ]
    
    def __init__(self, use_watson: bool = True):
        """
        Initialize classifier with compiled patterns
        
        Args:
            use_watson: Whether to use Watson Assistant if available
        """
        self.lifecycle_regex = [re.compile(p, re.IGNORECASE) for p in self.LIFECYCLE_PATTERNS]
        self.feature_regex = [re.compile(p, re.IGNORECASE) for p in self.FEATURE_PATTERNS]
        self.server_regex = [re.compile(p, re.IGNORECASE) for p in self.SERVER_PATTERNS]
        
        # Watson Assistant integration
        self.use_watson = use_watson and WATSON_AVAILABLE
        self.watson_service = None
        
        if self.use_watson:
            try:
                self.watson_service = get_watson_assistant_service()
                if self.watson_service.is_enabled():
                    logger.info("Watson Assistant enabled for query classification")
                else:
                    logger.info("Watson Assistant configured but not enabled")
                    self.use_watson = False
            except Exception as e:
                logger.warning(f"Failed to initialize Watson Assistant: {e}")
                self.use_watson = False
    
    def classify(self, query: str) -> QueryType:
        """
        Classify query type using Watson Assistant (if available) or regex patterns
        
        Args:
            query: User query string
            
        Returns:
            QueryType enum value
        """
        # Try Watson Assistant first if enabled
        if self.use_watson and self.watson_service:
            try:
                watson_result = self.watson_service.get_query_classification(query)
                if watson_result.get('success') and watson_result.get('confidence', 0) > 0.6:
                    query_type_str = watson_result.get('query_type', 'rag')
                    
                    if query_type_str == 'table_lookup':
                        logger.info(f"Watson classified as TABLE_LOOKUP (conf: {watson_result.get('confidence'):.2f}): {query[:50]}...")
                        return QueryType.TABLE_LOOKUP
                    elif query_type_str == 'metadata_lookup':
                        logger.info(f"Watson classified as METADATA_LOOKUP (conf: {watson_result.get('confidence'):.2f}): {query[:50]}...")
                        return QueryType.METADATA_LOOKUP
                    else:
                        logger.info(f"Watson classified as RAG (conf: {watson_result.get('confidence'):.2f}): {query[:50]}...")
                        return QueryType.RAG
            except Exception as e:
                logger.warning(f"Watson Assistant classification failed, falling back to regex: {e}")
        
        # Fallback to regex-based classification
        query_lower = query.lower()
        
        # Check for lifecycle/table queries
        if self._is_lifecycle_query(query):
            logger.info(f"Regex classified as TABLE_LOOKUP: {query[:50]}...")
            return QueryType.TABLE_LOOKUP
        
        # Check for feature availability queries
        if self._is_feature_query(query):
            logger.info(f"Regex classified as METADATA_LOOKUP: {query[:50]}...")
            return QueryType.METADATA_LOOKUP
        
        # Default to full RAG
        logger.info(f"Regex classified as RAG: {query[:50]}...")
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
        Uses Watson Assistant if available for better entity extraction
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with query_type, server_model, feature_code, mtm_options, etc.
        """
        # Try Watson Assistant first
        if self.use_watson and self.watson_service:
            try:
                watson_result = self.watson_service.get_query_classification(query)
                if watson_result.get('success'):
                    watson_entities = watson_result.get('entities', {})
                    
                    # Build intent from Watson results
                    intent = {
                        'query_type': watson_result.get('query_type', 'rag'),
                        'original_query': query,
                        'server_model': watson_entities.get('server_model'),
                        'mtm': watson_entities.get('mtm'),
                        'mtm_options': watson_result.get('mtm_options', []),
                        'feature_code': None,
                        'lifecycle_field': watson_entities.get('lifecycle_field'),
                        'confidence': watson_result.get('confidence', 0),
                        'source': 'watson_assistant',
                        'needs_clarification': watson_result.get('needs_clarification', False)
                    }
                    
                    # Don't fallback to regex - let the system ask for clarification instead
                    # This provides a better user experience than guessing
                    
                    logger.info(f"Watson intent extraction: {intent}")
                    return intent
            except Exception as e:
                logger.warning(f"Watson intent extraction failed: {e}")
        
        # If Watson is not available, detect query type but don't extract entities
        # Let the system ask for clarification instead of using regex
        query_type = self.classify(query)
        
        intent = {
            'query_type': query_type.value,
            'original_query': query,
            'server_model': None,
            'mtm': None,
            'mtm_options': [],
            'feature_code': None,
            'lifecycle_field': None,
            'confidence': 0.5,
            'source': 'regex_classification_only',
            'needs_clarification': True  # Always need clarification without Watson
        }
        
        logger.info(f"Regex classification (no entity extraction): {intent}")
        return intent
    
    def _extract_lifecycle_field(self, query: str) -> Optional[str]:
        """
        Determine which lifecycle field is being asked about
        
        Returns:
            'announced', 'available', 'withdrawn', 'discontinued', or 'end_of_support'
        """
        query_lower = query.lower()
        
        if 'announce' in query_lower:
            return 'announced'
        elif 'available' in query_lower or 'availability' in query_lower:
            return 'available'
        elif 'withdraw' in query_lower or 'withdrawal' in query_lower:
            return 'withdrawn'
        elif 'stop selling' in query_lower or 'stop marketing' in query_lower:
            return 'withdrawn'  # "stop selling" = marketing withdrawal
        elif 'discontinue' in query_lower or 'discontinuation' in query_lower:
            return 'discontinued'
        elif 'stop support' in query_lower or 'end support' in query_lower or 'end of support' in query_lower:
            return 'end_of_support'
        elif 'end of service' in query_lower or 'end of life' in query_lower:
            return 'end_of_support'
        
        return None


# Convenience function for quick classification
def classify_query(query: str) -> QueryType:
    """Quick classification without creating classifier instance"""
    classifier = QueryClassifier()
    return classifier.classify(query)


# Made with Bob