"""
Activation Feature Service
Handles queries about processor and memory activation features
Extracts feature codes and availability status from sales manual chunks
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ActivationFeature:
    """Represents an activation feature with its availability status"""
    
    def __init__(self, feature_code: str, description: str,
                 discontinued_date: Optional[str] = None,
                 chunk_text: str = "", metadata: Optional[Dict] = None):
        self.feature_code = feature_code
        self.description = description
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
            'discontinued_date': self.discontinued_date,
            'is_available': self.is_available,
            'status': self.status,
            'metadata': self.metadata
        }


class ActivationFeatureService:
    """Service for extracting and analyzing activation features"""
    
    # Patterns for feature codes (e.g., #EMB7, #EFA1)
    FEATURE_CODE_PATTERN = re.compile(r'#([A-Z0-9]{4})\b')
    
    # Patterns for discontinued dates
    DISCONTINUED_PATTERNS = [
        re.compile(r'No longer available as of ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE),
        re.compile(r'Discontinued as of ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE),
        re.compile(r'Withdrawn as of ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE),
        re.compile(r'No longer marketed as of ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE),
    ]
    
    # Keywords that indicate activation features
    ACTIVATION_KEYWORDS = [
        'activation',
        'activations',
        'memory activation',
        'processor activation',
        'cpu activation',
        'core activation',
        'capacity on demand',
        'cod',
    ]
    
    def __init__(self):
        """Initialize the activation feature service"""
        pass
    
    def is_activation_query(self, query: str) -> bool:
        """
        Determine if a query is asking about activation features
        
        Args:
            query: User query string
            
        Returns:
            True if query is about activations
        """
        query_lower = query.lower()
        
        # Check for activation keywords
        has_activation_keyword = any(keyword in query_lower for keyword in self.ACTIVATION_KEYWORDS)
        
        # Check for common activation query patterns
        activation_patterns = [
            r'(?:still\s+)?(?:sell|available|order)\s+.*activation',
            r'activation.*(?:still\s+)?(?:available|sold)',
            r'(?:processor|memory|cpu|core)\s+activation',
            r'can\s+(?:i|we)\s+(?:still\s+)?(?:buy|order|get)\s+.*activation',
        ]
        
        has_pattern = any(re.search(pattern, query_lower) for pattern in activation_patterns)
        
        return has_activation_keyword or has_pattern
    
    def extract_feature_from_chunk(self, chunk_text: str, metadata: Optional[Dict] = None) -> Optional[ActivationFeature]:
        """
        Extract activation feature information from a chunk
        
        Args:
            chunk_text: Text content of the chunk
            metadata: Chunk metadata
            
        Returns:
            ActivationFeature object or None if not an activation feature
        """
        # Check if this chunk is about activations
        if not any(keyword in chunk_text.lower() for keyword in self.ACTIVATION_KEYWORDS):
            return None
        
        # Extract feature code from the beginning (usually in heading)
        # Pattern: (#CODE) Description or #CODE Description
        feature_match = self.FEATURE_CODE_PATTERN.search(chunk_text[:200])
        if not feature_match:
            return None
        
        feature_code = feature_match.group(1)
        
        # Extract description (first line or up to first newline)
        # Keep the full line including the feature code for clarity
        lines = chunk_text.split('\n')
        description = lines[0].strip() if lines else ""
        
        # Only clean up if the description is just the feature code alone
        # Otherwise keep the full descriptive text
        if description == f"#{feature_code}" or description == f"(#{feature_code})":
            # If it's just the code, try to get more context from next line
            if len(lines) > 1:
                description = lines[1].strip()
        
        # Remove any leading/trailing whitespace
        description = description.strip()
        
        # Check for discontinued date
        discontinued_date = None
        for pattern in self.DISCONTINUED_PATTERNS:
            match = pattern.search(chunk_text)
            if match:
                discontinued_date = match.group(1)
                logger.info(f"Found discontinued date for {feature_code}: {discontinued_date}")
                break
        
        return ActivationFeature(
            feature_code=feature_code,
            description=description,
            discontinued_date=discontinued_date,
            chunk_text=chunk_text,
            metadata=metadata or {}
        )
    
    def extract_features_from_chunks(self, chunks: List[Dict]) -> List[ActivationFeature]:
        """
        Extract all activation features from a list of chunks
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
            
        Returns:
            List of ActivationFeature objects
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
                logger.info(f"Extracted feature: {feature.feature_code} - {feature.status}")
        
        return features
    
    def categorize_features(self, features: List[ActivationFeature]) -> Dict[str, List[ActivationFeature]]:
        """
        Categorize features by type (processor, memory, etc.)
        
        Args:
            features: List of ActivationFeature objects
            
        Returns:
            Dictionary with categories as keys
        """
        categories = {
            'processor': [],
            'memory': [],
            'other': []
        }
        
        for feature in features:
            desc_lower = feature.description.lower()
            chunk_lower = feature.chunk_text.lower()
            
            if any(word in desc_lower or word in chunk_lower 
                   for word in ['processor', 'cpu', 'core', 'proc']):
                categories['processor'].append(feature)
            elif any(word in desc_lower or word in chunk_lower 
                     for word in ['memory', 'ram', 'ddr']):
                categories['memory'].append(feature)
            else:
                categories['other'].append(feature)
        
        return categories
    
    def format_activation_summary(self, features: List[ActivationFeature], 
                                  query: str = "") -> Dict:
        """
        Format activation features into a user-friendly summary
        
        Args:
            features: List of ActivationFeature objects
            query: Original user query
            
        Returns:
            Dictionary with formatted summary
        """
        if not features:
            return {
                'success': False,
                'message': 'No activation features found',
                'features': [],
                'summary': {
                    'total': 0,
                    'available': 0,
                    'discontinued': 0
                }
            }
        
        # Categorize features
        categories = self.categorize_features(features)
        
        # Count available vs discontinued
        available = [f for f in features if f.is_available]
        discontinued = [f for f in features if not f.is_available]
        
        # Build summary
        summary = {
            'success': True,
            'query': query,
            'features': [f.to_dict() for f in features],
            'categories': {
                'processor': [f.to_dict() for f in categories['processor']],
                'memory': [f.to_dict() for f in categories['memory']],
                'other': [f.to_dict() for f in categories['other']]
            },
            'summary': {
                'total': len(features),
                'available': len(available),
                'discontinued': len(discontinued),
                'by_category': {
                    'processor': len(categories['processor']),
                    'memory': len(categories['memory']),
                    'other': len(categories['other'])
                }
            }
        }
        
        # Add human-readable message
        if available:
            summary['message'] = f"Found {len(available)} available activation feature(s)"
            if discontinued:
                summary['message'] += f" and {len(discontinued)} discontinued feature(s)"
        else:
            summary['message'] = f"All {len(discontinued)} activation features found are discontinued"
        
        return summary
    
    def generate_activation_answer(self, features: List[ActivationFeature], 
                                   query: str = "") -> str:
        """
        Generate a natural language answer about activation features
        
        Args:
            features: List of ActivationFeature objects
            query: Original user query
            
        Returns:
            Natural language answer string
        """
        if not features:
            return "I couldn't find any activation features in the sales manual for this server."
        
        # Categorize
        categories = self.categorize_features(features)
        available = [f for f in features if f.is_available]
        discontinued = [f for f in features if not f.is_available]
        
        # Build answer
        answer_parts = []
        
        # Summary
        if available and discontinued:
            answer_parts.append(
                f"I found {len(features)} activation features: "
                f"{len(available)} currently available and {len(discontinued)} discontinued."
            )
        elif available:
            answer_parts.append(
                f"I found {len(available)} activation feature(s) that are currently available."
            )
        else:
            answer_parts.append(
                f"I found {len(discontinued)} activation feature(s), but all are discontinued."
            )
        
        # Available features
        if available:
            answer_parts.append("\n\n<strong>Currently Available:</strong>")
            for feature in available:
                answer_parts.append(f"- <strong>{feature.feature_code}</strong>: {feature.description}")
        
        # Discontinued features
        if discontinued:
            answer_parts.append("\n\n<strong>Discontinued:</strong>")
            for feature in discontinued:
                answer_parts.append(
                    f"- <strong>{feature.feature_code}</strong>: {feature.description} "
                    f"(No longer available as of {feature.discontinued_date})"
                )
        
        return "\n".join(answer_parts)


# Convenience function
def extract_activation_features(chunks: List[Dict]) -> List[ActivationFeature]:
    """Quick extraction without creating service instance"""
    service = ActivationFeatureService()
    return service.extract_features_from_chunks(chunks)


# Made with Bob