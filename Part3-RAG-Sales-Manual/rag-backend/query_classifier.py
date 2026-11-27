"""
Query Classifier for Hybrid RAG System
Routes queries to appropriate handlers: table lookup, metadata lookup, or full RAG
Enhanced with Watson Assistant integration for superior NLP
"""

import re
import logging
from typing import Dict, Optional, List
from enum import Enum

from intent_extractor import find_servers, llm_extract, variant_options

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
    ACTIVATION_LOOKUP = "activation_lookup"
    PHYSICAL_FEATURE_LOOKUP = "physical_feature_lookup"
    RAG = "rag"


class QueryClassifier:
    """Classify queries to route to appropriate handler"""
    
    # Patterns for lifecycle/table queries
    LIFECYCLE_PATTERNS = [
        r"when\s+(?:was|is|will)\s+.*(?:announced|available|withdrawn|discontinued)",
        r"(?:announcement|availability|withdrawal|discontinuation|support\s+level)\s+date",
        r"what\s+(?:is|was)\s+the\s+(?:announcement|availability|withdrawal|support\s+level)\s+date",
        r"when\s+(?:did|does|will)\s+.*(?:announce|become\s+available|withdraw)",
        r"when\s+(?:did|does|will)\s+.*stop\s+(?:supporting|selling)",
        r"when\s+(?:was|is)\s+.*(?:end\s+of\s+(?:life|support|service|marketing))",
        r"(?:end\s+of\s+(?:life|support|service|marketing))\s+date",
        r"stop\s+support(?:ing)?",  # Added: "stop supporting"
        r"end(?:ed)?\s+support",     # Added: "end support", "ended support"
        r"no\s+longer\s+support",    # Added: "no longer support"
        r"support\s+level\s+change[ds]?",  # Added: "support level changed", "support level change"
        r"change(?:d)?\s+support\s+level", # Added: "changed support level"
    ]
    
    # Patterns for activation feature queries
    ACTIVATION_PATTERNS = [
        r"(?:still\s+)?(?:sell|available|order)\s+.*activation",
        r"activation.*(?:still\s+)?(?:available|sold)",
        r"(?:processor|memory|cpu|core)\s+activation",
        r"can\s+(?:i|we)\s+(?:still\s+)?(?:buy|order|get)\s+.*activation",
        r"what\s+activation.*(?:available|offered)",
        r"list.*activation",
        r"show.*activation",
    ]
    
    # Patterns for feature code queries — availability, withdrawal, AND description
    # Matches both "(#0010)" and "0010" and "feature code 0010" styles
    _FC = r"#?[A-Z0-9]{4}"  # feature code token: optional # + 4 alphanumeric chars
    FEATURE_PATTERNS = [
        rf"is\s+(?:feature\s+)?(?:code\s+)?{_FC}\s+(?:still\s+)?available",
        rf"can\s+(?:i|we)\s+(?:still\s+)?order\s+(?:feature\s+)?(?:code\s+)?{_FC}",
        rf"(?:feature\s+)?(?:code\s+)?{_FC}\s+(?:withdrawal|discontinued)",
        rf"when\s+(?:was|is)\s+(?:feature\s+)?(?:code\s+)?{_FC}\s+withdrawn",
        # "What is feature code #0010 / 0010 / (#0010)"
        rf"what\s+is\s+(?:feature\s+)?(?:code\s+)?{_FC}",
        rf"(?:tell|describe|explain)\s+.*?(?:feature\s+)?(?:code\s+)?{_FC}",
        rf"(?:feature\s+)?(?:code\s+)?{_FC}.*?(?:description|details?|info)",
    ]
    
    # Which part of a family's index a RAG question should draw on. Feature-code chunks are ~90% of
    # an index, so a general question ("maximum memory", "operating systems") must not be left to
    # compete with them; a feature question ("which adapters / feature codes ...") needs them.
    SCOPE_FEATURE = 'feature'    # asks for feature codes / part numbers: feature chunks first
    SCOPE_MIXED = 'mixed'        # may be about orderable options: both kinds
    SCOPE_GENERAL = 'general'    # specifications, requirements, overview: narrative sections first

    # Unmistakable: a code (#EFP1, (#0010), "feature code 0010"), "feature code(s)", FC, CCIN, part number
    _STRONG_FEATURE = re.compile(
        r"\(?#[A-Z0-9]{4}\b|\bfeature\s+(?:codes?|numbers?)\b|\bFCs?\b|\bCCINs?\b|\bpart\s+numbers?\b",
        re.IGNORECASE)
    # Hints at orderable options. "features" alone also means "highlights", so this stays mixed.
    _WEAK_FEATURE = re.compile(
        r"\bfeatures?\b|\boptions?\b|\border(?:s|ed|ing|able)?\b|\badapters?\b|\bcards?\b|\bc?dimms?\b"
        r"|\btransceivers?\b|\bcables?\b|\bnvme\b|\bdrives?\b",
        re.IGNORECASE)

    # Questions about operating-system levels are answered by one section, "Software requirements".
    # Feature chunks mention "AIX" or "Linux" all over, so name the section instead of searching for it.
    _OS_TERMS = {
        'aix': re.compile(r"\bAIX\b", re.IGNORECASE),
        'ibm i': re.compile(r"\bIBM\s*i\b", re.IGNORECASE),
        'linux': re.compile(r"\b(?:Linux|RHEL|Red\s*Hat|SUSE|SLES)\b", re.IGNORECASE),
        'vios': re.compile(r"\bVIOS\b|\bVirtual\s+I/O\s+Server\b", re.IGNORECASE),
    }
    _OS_GENERIC = re.compile(r"\boperating\s+systems?\b", re.IGNORECASE)
    _LEVEL_WORDS = re.compile(
        r"\b(?:levels?|versions?|releases?|minimum|oldest|latest|require[ds]?|need(?:s|ed)?|supports?|supported|"
        r"TL|technology\s+(?:level|release)|service\s+packs?|PTFs?|or\s+later)\b", re.IGNORECASE)
    SOFTWARE_SECTION = 'Software requirements'

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
        self.activation_regex = [re.compile(p, re.IGNORECASE) for p in self.ACTIVATION_PATTERNS]
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
        
        # Check for activation queries
        if self._is_activation_query(query):
            logger.info(f"Regex classified as ACTIVATION_LOOKUP: {query[:50]}...")
            return QueryType.ACTIVATION_LOOKUP
        
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
    
    def _is_activation_query(self, query: str) -> bool:
        """Check if query is about activation features"""
        return any(regex.search(query) for regex in self.activation_regex)
    
    def _is_feature_query(self, query: str) -> bool:
        """Check if query is about feature availability"""
        return any(regex.search(query) for regex in self.feature_regex)
    
    def retrieval_scope(self, query: str) -> str:
        """SCOPE_FEATURE, SCOPE_MIXED or SCOPE_GENERAL: which kind of chunks a RAG search should favour."""
        if self._STRONG_FEATURE.search(query):
            return self.SCOPE_FEATURE
        if self._WEAK_FEATURE.search(query):
            return self.SCOPE_MIXED
        return self.SCOPE_GENERAL

    def section_hint(self, query: str) -> Optional[Dict[str, any]]:  # type: ignore
        """The manual section a question is about, with the operating systems it names, or None.

        {'section': 'Software requirements', 'terms': ['aix']}; terms is empty for "which operating systems".
        """
        if not self._LEVEL_WORDS.search(query):
            return None
        terms = [name for name, rx in self._OS_TERMS.items() if rx.search(query)]
        if not terms and not self._OS_GENERIC.search(query):
            return None
        return {'section': self.SOFTWARE_SECTION, 'terms': terms}

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
        Extract feature code from query.
        Handles all common user formats:
          (#0010)  #0010  0010  feature code 0010  feature code #0010
        
        Returns:
            Feature code without # prefix, uppercased (e.g., "0010", "EFA1") or None
        """
        # Prefer explicit "(#XXXX)" or "#XXXX" form first
        match = re.search(r'\(#([A-Z0-9]{4})\)', query, re.IGNORECASE)
        if not match:
            match = re.search(r'#([A-Z0-9]{4})\b', query, re.IGNORECASE)
        # Fall back to bare 4-char code after "feature code" or "code"
        if not match:
            match = re.search(r'(?:feature\s+)?code\s+([A-Z0-9]{4})\b', query, re.IGNORECASE)
        # Last resort: standalone 4-char alphanumeric word
        if not match:
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
                        'retrieval_scope': self.retrieval_scope(query),
                        'section_hint': self.section_hint(query),
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
        
        # Watson is not available: exact server tokens from sources.json plus regex, and
        # the LLM (intent_extractor) for free-text wording the regex cannot handle.
        query_type = self.classify(query).value
        lifecycle_field = self._single_lifecycle_field(query)
        servers = find_servers(query)
        server_model, mtm = servers[0] if len(servers) == 1 else (None, None)
        source = 'deterministic'
        
        # Shortcut: exact server, a lifecycle regex hit and exactly one kind of date
        # mentioned. Anything else (typos, other wording, two dates) goes to the LLM.
        settled = query_type == QueryType.TABLE_LOOKUP.value and server_model and lifecycle_field
        llm = None if settled else llm_extract(query)
        if llm:
            source = 'llm'
            # An exact server token in the question beats the LLM's reading of it.
            server_model = server_model or llm['server_model']
            # Regex hits for activation / feature-code questions stand; the LLM refines the rest.
            if query_type in (QueryType.RAG.value, QueryType.TABLE_LOOKUP.value):
                query_type = llm['query_type'] or query_type
            lifecycle_field = llm['lifecycle_field'] or lifecycle_field
        
        intent = {
            'query_type': query_type,
            'original_query': query,
            'server_model': server_model,
            'mtm': mtm,
            # Keyword rewrite of the question for retrieval (LLM only; None if unavailable)
            'search_query': llm.get('search_query') if llm else None,
            # "S924" alone could be the A or the G model (different MTMs, different manuals)
            'mtm_options': variant_options(server_model) if server_model and not mtm else [],
            'feature_code': None,
            # Which chunks a RAG search should favour (feature-code chunks vs narrative sections)
            'retrieval_scope': self.retrieval_scope(query),
            'section_hint': self.section_hint(query),
            'lifecycle_field': lifecycle_field if query_type == QueryType.TABLE_LOOKUP.value else None,
            'confidence': 0.9 if server_model else 0.5,
            'source': source,
            'needs_clarification': server_model is None
        }
        
        logger.info(f"Intent ({source}): {intent}")
        return intent
    
    # Wording for each lifecycle date. A question counts as clear only if it hits one field.
    LIFECYCLE_KEYWORDS = {
        'announced': ('announce',),
        'available': ('available', 'availability'),
        'withdrawn': ('withdraw', 'no longer sell', 'end of marketing', 'stop selling', 'stop marketing'),
        'support_level_changed': ('support level', 'support changed'),
        'discontinued': ('discontinue', 'discontinuation'),
        'end_of_support': ('stopped supporting', 'no longer support', 'stop support', 'end support',
                           'end of support', 'end of service', 'end of life', 'standard support'),
    }

    def _single_lifecycle_field(self, query: str) -> Optional[str]:
        """The lifecycle field if the question mentions exactly one kind of date, else None."""
        query_lower = query.lower()
        hits = {field for field, words in self.LIFECYCLE_KEYWORDS.items()
                if any(w in query_lower for w in words)}
        return hits.pop() if len(hits) == 1 else None

    def _extract_lifecycle_field(self, query: str) -> Optional[str]:
        """
        Determine which lifecycle field is being asked about
        
        Returns:
            'announced', 'available', 'withdrawn', 'discontinued', or 'end_of_support'
        """
        query_lower = query.lower()
        
        if 'announce' in query_lower:
            return 'announced'
        elif 'stopped supporting' in query_lower or 'no longer support' in query_lower:
            return 'end_of_support'
        elif 'no longer sell' in query_lower or 'end of marketing' in query_lower:
            return 'withdrawn'
        elif 'available' in query_lower or 'availability' in query_lower:
            return 'available'
        elif 'withdraw' in query_lower or 'withdrawal' in query_lower:
            return 'withdrawn'
        elif 'stop selling' in query_lower or 'stop marketing' in query_lower:
            return 'withdrawn'  # "stop selling" = marketing withdrawal
        elif 'support level' in query_lower or 'support changed' in query_lower:
            return 'support_level_changed'
        elif 'discontinue' in query_lower or 'discontinuation' in query_lower:
            return 'discontinued'
        elif 'stop support' in query_lower or 'end support' in query_lower or 'end of support' in query_lower:
            return 'end_of_support'
        elif 'end of service' in query_lower or 'end of life' in query_lower or 'standard support' in query_lower:
            return 'end_of_support'
        
        return None


# Convenience function for quick classification
def classify_query(query: str) -> QueryType:
    """Quick classification without creating classifier instance"""
    classifier = QueryClassifier()
    return classifier.classify(query)


# Made with Bob