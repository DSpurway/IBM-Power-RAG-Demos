"""
Physical Feature Service
Handles queries about physical processor and memory features (non-activation)
Extracts feature codes and availability status from sales manual chunks
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PhysicalFeature:
    """Represents a physical feature (processor or memory) with its availability status"""
    
    def __init__(self, feature_code: str, description: str,
                 feature_type: str = "unknown",
                 discontinued_date: Optional[str] = None,
                 chunk_text: str = "", metadata: Optional[Dict] = None):
        self.feature_code = feature_code
        self.description = description
        self.feature_type = feature_type  # 'processor', 'memory', or 'other'
        self.discontinued_date = discontinued_date
        self.is_available = discontinued_date is None
        self.chunk_text = chunk_text
        self.metadata = metadata or {}
        self.status = 'Available' if self.is_available else f'Discontinued ({self.discontinued_date})'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'feature_code': self.feature_code,
            'description': self.description,
            'feature_type': self.feature_type,
            'discontinued_date': self.discontinued_date,
            'is_available': self.is_available,
            'status': self.status,
            'metadata': self.metadata
        }


class PhysicalFeatureService:
    """Service for extracting and analyzing physical features"""
    
    # Patterns for feature codes (e.g., #EM8K, #EFP4)
    FEATURE_CODE_PATTERN = re.compile(r'#([A-Z0-9]{4})\b')
    
    # Patterns for discontinued dates
    DISCONTINUED_PATTERNS = [
        re.compile(r'No longer available as of ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE),
        re.compile(r'Discontinued as of ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE),
        re.compile(r'Withdrawn as of ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE),
        re.compile(r'No longer marketed as of ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE),
    ]
    
    # Keywords that indicate processor features
    PROCESSOR_KEYWORDS = [
        'processor',
        'core',
        'cores',
        'scm',
        'ghz',
        'power9',
        'power10',
        'power11',
    ]
    
    # Keywords that indicate memory features
    MEMORY_KEYWORDS = [
        'memory',
        'gb',
        'cdimm',
        'dimm',
        'ddr',
        'dram',
    ]
    
    # Keywords to EXCLUDE (activation features)
    ACTIVATION_KEYWORDS = [
        'activation',
        'activations',
        'cod',
        'capacity on demand',
    ]
    
    def __init__(self):
        """Initialize the physical feature service"""
        pass
    
    def is_physical_feature_query(self, query: str) -> bool:
        """
        Determine if a query is asking about physical features
        
        Args:
            query: User query string
            
        Returns:
            True if query is about physical features
        """
        query_lower = query.lower()
        
        # Must NOT be about activations
        if any(keyword in query_lower for keyword in self.ACTIVATION_KEYWORDS):
            return False
        
        # Check for processor or memory keywords
        has_processor = any(keyword in query_lower for keyword in self.PROCESSOR_KEYWORDS)
        has_memory = any(keyword in query_lower for keyword in self.MEMORY_KEYWORDS)
        
        # Check for common physical feature query patterns
        physical_patterns = [
            r'(?:still\s+)?(?:sell|available|order)\s+.*(?:processor|memory|core)',
            r'(?:processor|memory).*(?:still\s+)?(?:available|sold)',
            r'can\s+(?:i|we)\s+(?:still\s+)?(?:buy|order|get)\s+.*(?:processor|memory)',
            r'what\s+(?:processor|memory).*(?:available|offered)',
        ]
        
        has_pattern = any(re.search(pattern, query_lower) for pattern in physical_patterns)
        
        return (has_processor or has_memory) and has_pattern
    
    def extract_feature_from_chunk(self, chunk_text: str, metadata: Optional[Dict] = None) -> Optional[PhysicalFeature]:
        """
        Extract physical feature information from a chunk
        
        Args:
            chunk_text: Text content of the chunk
            metadata: Chunk metadata
            
        Returns:
            PhysicalFeature object or None if not a physical feature
        """
        chunk_lower = chunk_text.lower()
        
        # Must have processor or memory keywords
        has_processor = any(keyword in chunk_lower for keyword in self.PROCESSOR_KEYWORDS)
        has_memory = any(keyword in chunk_lower for keyword in self.MEMORY_KEYWORDS)
        
        if not (has_processor or has_memory):
            return None
        
        # Extract feature code from the beginning
        feature_match = self.FEATURE_CODE_PATTERN.search(chunk_text[:200])
        if not feature_match:
            return None
        
        feature_code = feature_match.group(1)
        
        # Skip if this is specifically an activation feature
        # Only check the first line (header) where the feature is described
        first_line = chunk_text.split('\n')[0].lower() if chunk_text else ""
        if any(keyword in first_line for keyword in self.ACTIVATION_KEYWORDS):
            logger.debug(f"Skipping {feature_code} - activation keyword in header: {first_line[:100]}")
            return None
        
        # Extract description (first line, keep full text)
        lines = chunk_text.split('\n')
        description = lines[0].strip() if lines else ""
        
        # Only clean up if the description is just the feature code alone
        if description == f"#{feature_code}" or description == f"(#{feature_code})":
            if len(lines) > 1:
                description = lines[1].strip()
        
        description = description.strip()
        
        # Determine feature type
        feature_type = 'other'
        if has_processor:
            feature_type = 'processor'
        elif has_memory:
            feature_type = 'memory'
        
        # Check for discontinued date
        discontinued_date = None
        for pattern in self.DISCONTINUED_PATTERNS:
            match = pattern.search(chunk_text)
            if match:
                discontinued_date = match.group(1)
                logger.info(f"Found discontinued date for {feature_code}: {discontinued_date}")
                break
        
        return PhysicalFeature(
            feature_code=feature_code,
            description=description,
            feature_type=feature_type,
            discontinued_date=discontinued_date,
            chunk_text=chunk_text,
            metadata=metadata or {}
        )
    
    def extract_features_from_chunks(self, chunks: List[Dict]) -> List[PhysicalFeature]:
        """
        Extract all physical features from a list of chunks
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
            
        Returns:
            List of PhysicalFeature objects
        """
        features = []
        seen_codes = set()
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            
            feature = self.extract_feature_from_chunk(chunk_text, metadata)
            if feature and feature.feature_code not in seen_codes:
                features.append(feature)
                seen_codes.add(feature.feature_code)
                logger.info(f"Extracted physical feature: {feature.feature_code} ({feature.feature_type}) - {feature.status}")
        
        return features
    
    def categorize_features(self, features: List[PhysicalFeature]) -> Dict[str, List[PhysicalFeature]]:
        """
        Categorize features by type
        
        Args:
            features: List of PhysicalFeature objects
            
        Returns:
            Dictionary with categories as keys
        """
        categories = {
            'processor': [],
            'memory': [],
            'other': []
        }
        
        for feature in features:
            categories[feature.feature_type].append(feature)
        
        return categories
    
    def generate_physical_feature_answer(self, features: List[PhysicalFeature], 
                                         query: str = "") -> str:
        """
        Generate a natural language answer about physical features
        
        Args:
            features: List of PhysicalFeature objects
            query: Original user query
            
        Returns:
            Natural language answer string
        """
        if not features:
            return "I couldn't find any physical processor or memory features in the sales manual for this server."
        
        # Categorize
        categories = self.categorize_features(features)
        available = [f for f in features if f.is_available]
        discontinued = [f for f in features if not f.is_available]
        
        # Build answer
        answer_parts = []
        
        # Summary
        if available and discontinued:
            answer_parts.append(
                f"I found {len(features)} physical features: "
                f"{len(available)} currently available and {len(discontinued)} discontinued."
            )
        elif available:
            answer_parts.append(
                f"I found {len(available)} physical feature(s) that are currently available."
            )
        else:
            answer_parts.append(
                f"I found {len(discontinued)} physical feature(s), but all are discontinued."
            )
        
        # Available features by category
        if available:
            answer_parts.append("\n\n<strong>Currently Available:</strong>")
            
            # Processors
            available_processors = [f for f in categories['processor'] if f.is_available]
            if available_processors:
                answer_parts.append("\n<em>Processors:</em>")
                for feature in available_processors:
                    answer_parts.append(f"- <strong>{feature.feature_code}</strong>: {feature.description}")
            
            # Memory
            available_memory = [f for f in categories['memory'] if f.is_available]
            if available_memory:
                answer_parts.append("\n<em>Memory:</em>")
                for feature in available_memory:
                    answer_parts.append(f"- <strong>{feature.feature_code}</strong>: {feature.description}")
        
        # Discontinued features by category
        if discontinued:
            answer_parts.append("\n\n<strong>Discontinued:</strong>")
            
            # Processors
            discontinued_processors = [f for f in categories['processor'] if not f.is_available]
            if discontinued_processors:
                answer_parts.append("\n<em>Processors:</em>")
                for feature in discontinued_processors:
                    answer_parts.append(
                        f"- <strong>{feature.feature_code}</strong>: {feature.description} "
                        f"(No longer available as of {feature.discontinued_date})"
                    )
            
            # Memory
            discontinued_memory = [f for f in categories['memory'] if not f.is_available]
            if discontinued_memory:
                answer_parts.append("\n<em>Memory:</em>")
                for feature in discontinued_memory:
                    answer_parts.append(
                        f"- <strong>{feature.feature_code}</strong>: {feature.description} "
                        f"(No longer available as of {feature.discontinued_date})"
                    )
        
        return "\n".join(answer_parts)


# Convenience function
def extract_physical_features(chunks: List[Dict]) -> List[PhysicalFeature]:
    """Quick extraction without creating service instance"""
    service = PhysicalFeatureService()
    return service.extract_features_from_chunks(chunks)


# Made with Bob