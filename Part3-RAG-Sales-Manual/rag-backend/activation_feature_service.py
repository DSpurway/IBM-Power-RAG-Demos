"""
Activation Feature Service
Handles queries about processor and memory activation features
Extracts feature codes and availability status from sales manual chunks
Enhanced with LLM-based description generation for clearer output
"""

import re
import logging
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# LLM Configuration for description generation
# IMPORTANT: Use Granite service (not TinyLlama) for better quality descriptions
GRANITE_HOST = os.environ.get('GRANITE_HOST', 'granite-llama-service')
GRANITE_PORT = os.environ.get('GRANITE_PORT', '8080')


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
            'metadata': self.metadata,
            'chunk_text': self.chunk_text  # Full Sales Manual text for detail view
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
        ' proc act ',
        ' mem act ',
        'base proc act',
        'proc act',
        'memory act',
    ]
    
    def __init__(self, use_llm_descriptions: bool = True, max_llm_calls: int = 1):
        """
        Initialize the activation feature service
        
        Args:
            use_llm_descriptions: Whether to use LLM to generate cleaner descriptions
            max_llm_calls: Maximum number of LLM calls to make (default: 1 for line-by-line behavior)
        """
        self.use_llm_descriptions = use_llm_descriptions
        self.max_llm_calls = max_llm_calls
        self.llm_calls_made = 0
        self.llm_url = f"http://{GRANITE_HOST}:{GRANITE_PORT}/v1/completions"
    
    def _extract_feature_excerpt(self, feature_code: str, chunk_text: str) -> str:
        """
        Extract only the small feature-local excerpt needed for description generation.

        Target structure from Sales Manual:
        1. Title line: "(#CODE) Description"
        2. Optional second line: "Each occurrence..." or discontinuation notice
        3. "Attributes provided:" line (useful for LLM context)
        
        Stop at "Attributes required:" (not useful for description)
        """
        lines = chunk_text.split('\n')
        excerpt_lines = []
        found_feature_line = False

        for line in lines[:25]:
            line_stripped = line.strip()

            if not found_feature_line:
                if f"#{feature_code}" in line or f"(#{feature_code})" in line:
                    found_feature_line = True
                    if line_stripped:
                        excerpt_lines.append(line_stripped)
                continue

            # Stop at empty line
            if not line_stripped:
                break

            # Stop at "Attributes required" and beyond (not useful)
            if (line_stripped.lower().startswith('attributes required:') or
                line_stripped.lower().startswith('minimum required:') or
                line_stripped.lower().startswith('maximum allowed:') or
                line_stripped.lower().startswith('os level required:') or
                line_stripped.lower().startswith('initial order/mes/both/supported:') or
                line_stripped.lower().startswith('csu:') or
                line_stripped.lower().startswith('return parts')):
                break

            # Include "Attributes provided" line (useful for LLM)
            excerpt_lines.append(line_stripped)

            # Stop after "Attributes provided" line
            if line_stripped.lower().startswith('attributes provided:'):
                break

            # Limit to reasonable length (title + description + attributes provided)
            if len(excerpt_lines) >= 4:
                break

        if not excerpt_lines:
            return chunk_text[:1000]

        excerpt = '\n'.join(excerpt_lines)
        return excerpt[:1000]

    def _generate_llm_description(self, feature_code: str, raw_text: str) -> Optional[str]:
        """
        Use Granite LLM to generate a clear, concise description from a focused feature excerpt
        
        Args:
            feature_code: The feature code (e.g., EDAR, ELCP)
            raw_text: Raw text from the sales manual chunk
            
        Returns:
            Clean description or None if generation fails
        """
        if not self.use_llm_descriptions:
            return None
        
        # Check if we've exceeded the maximum number of LLM calls
        if self.llm_calls_made >= self.max_llm_calls:
            logger.warning(f"Skipping LLM description for {feature_code} - max calls ({self.max_llm_calls}) reached")
            return None

        feature_excerpt = self._extract_feature_excerpt(feature_code, raw_text)
        
        try:
            prompt = f"""Based on the following IBM Power Systems sales manual excerpt for feature code #{feature_code}, provide exactly one short sentence describing what this activation feature is for.

Sales Manual Excerpt:
{feature_excerpt}

Requirements:
- Return exactly one sentence
- Maximum 25 words
- State the activation type and capacity/amount
- Include only the most important restriction if present
- Do not include the feature code
- Do not add explanations, headings, or extra text

Description:"""

            import time
            start_time = time.time()
            logger.info(f"Requesting Granite LLM description for {feature_code} (call {self.llm_calls_made + 1}/{self.max_llm_calls}, excerpt_len={len(feature_excerpt)})")
            self.llm_calls_made += 1
            
            response = requests.post(
                self.llm_url,
                json={
                    "prompt": prompt,
                    "max_tokens": 32,
                    "temperature": 0.1,
                    "stop": ["\n", "\n\n", "Feature Code:", "Sales Manual", "Description:"]
                },
                timeout=30
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Granite LLM response received in {elapsed_time:.2f} seconds")
            
            if response.status_code == 200:
                result = response.json()
                description = result.get('choices', [{}])[0].get('text', '').strip()
                
                description = description.replace('\n', ' ')
                description = re.sub(r'\s+', ' ', description)
                description = description.strip('"\'.,;: ')
                
                if description and 20 <= len(description) <= 500:
                    logger.info(f"Generated Granite description for {feature_code}: {description[:100]}...")
                    return description
                else:
                    logger.warning(f"Granite description length invalid for {feature_code}: {len(description)} chars")
                    return None
            else:
                logger.warning(f"Granite LLM request failed with status {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Granite LLM timeout for {feature_code} - skipping (Granite service may be overloaded)")
            return None
        except Exception as e:
            logger.warning(f"Failed to generate Granite description for {feature_code}: {e}")
            return None
    
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
        chunk_text_lower = chunk_text.lower()

        # Check if this chunk is about activations
        if not any(keyword in chunk_text_lower for keyword in self.ACTIVATION_KEYWORDS):
            return None
        
        # Extract feature code from the beginning (usually in heading)
        # Pattern: (#CODE) Description or #CODE Description
        feature_match = self.FEATURE_CODE_PATTERN.search(chunk_text[:500])
        if not feature_match:
            return None
        
        feature_code = feature_match.group(1)
        
        feature_excerpt = self._extract_feature_excerpt(feature_code, chunk_text)

        # Try to generate a clean description using LLM first
        llm_description = self._generate_llm_description(feature_code, chunk_text)
        
        if llm_description:
            description = llm_description
        else:
            # Manual extraction based on Sales Manual structure:
            # Line 1: "(#EPS2) 1 core Base Proc Act (Pools 2.0) for #EDP4 any OS (from Static)"
            # Line 2: "Each occurrence of this feature will permanently activate..."
            # We want just Line 1 (the title) without the feature code prefix
            
            lines = feature_excerpt.split('\n')
            description = None
            
            # Find the title line with the feature code
            for line in lines[:5]:  # Check first 5 lines only
                line_stripped = line.strip()
                
                # Skip empty lines and page references
                if not line_stripped or re.match(r'^\(Part\s+\d+/\d+\)', line_stripped):
                    continue
                
                # Found the title line with feature code
                if f"#{feature_code}" in line or f"(#{feature_code})" in line:
                    # Extract and clean the description
                    description = line_stripped
                    
                    # Remove the feature code prefix: "(#EPS2) " or "#EPS2 "
                    description = re.sub(rf'^\(#{feature_code}\)\s*', '', description)
                    description = re.sub(rf'^#{feature_code}\s*', '', description)
                    
                    # Remove any leading/trailing punctuation
                    description = description.strip(':-., ')
                    
                    break
            
            # If we didn't find a description, try a more lenient search
            if not description:
                for line in lines[:10]:
                    line_stripped = line.strip()
                    if line_stripped and len(line_stripped) > 20:
                        # Check if it looks like a description (has "activation" or similar)
                        if any(word in line_stripped.lower() for word in ['activation', 'memory', 'processor', 'core']):
                            description = line_stripped
                            # Clean up feature code if present
                            description = re.sub(rf'^\(#{feature_code}\)\s*', '', description)
                            description = re.sub(rf'^#{feature_code}\s*', '', description)
                            break
            
            # Final cleanup
            if description:
                # Remove page/part references
                description = re.sub(r'\s*\(Part\s+\d+/\d+\)', '', description)
                description = re.sub(r'\s*\(Page\s+\d+/\d+\)', '', description)
                
                # Remove "Feature Code:" prefix if somehow present
                description = re.sub(r'^Feature Code:\s*#?[A-Z0-9]{4}\s*Name:\s*', '', description, flags=re.IGNORECASE)
                
                # Handle table formatting (pipes)
                if '|' in description and description.count('|') > 2:
                    parts = [p.strip() for p in description.split('|') if p.strip()]
                    for part in parts:
                        if any(word in part.lower() for word in ['activation', 'memory', 'processor', 'core', 'gb']):
                            description = part
                            break
                
                # Clean up whitespace
                description = re.sub(r'\s+', ' ', description).strip()
                
                # Truncate if too long (keep it concise)
                if len(description) > 120:
                    # Try to break at a natural point
                    if ' for ' in description:
                        # Keep everything up to and including "for X"
                        parts = description.split(' for ')
                        if len(parts) >= 2:
                            description = parts[0] + ' for ' + parts[1].split()[0]
                    elif len(description) > 150:
                        description = description[:147] + '...'
            else:
                # Last resort: use first non-empty line
                for line in lines:
                    if line.strip() and len(line.strip()) > 10:
                        description = line.strip()
                        break
                
                if not description:
                    description = f"Activation feature {feature_code}"
        
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
        
        # Reset LLM call counter for this extraction batch
        self.llm_calls_made = 0
        
        logger.info(f"Processing {len(chunks)} chunks for activation features (max {self.max_llm_calls} LLM calls)")
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            
            feature_match = self.FEATURE_CODE_PATTERN.search(chunk_text[:500])
            if feature_match and feature_match.group(1) in seen_codes:
                logger.info(f"Skipping duplicate feature chunk for {feature_match.group(1)} before LLM extraction")
                continue

            feature = self.extract_feature_from_chunk(chunk_text, metadata)
            if feature and feature.feature_code not in seen_codes:
                features.append(feature)
                seen_codes.add(feature.feature_code)
                logger.info(f"Extracted feature {len(features)}: {feature.feature_code} - {feature.status}")
        
        logger.info(f"Extraction complete: {len(features)} features found, {self.llm_calls_made} LLM calls made")
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
            Natural language answer string with AI-generated disclaimer
        """
        if not features:
            return "I couldn't find any activation features in the sales manual for this server."
        
        # Categorize
        categories = self.categorize_features(features)
        available = [f for f in features if f.is_available]
        discontinued = [f for f in features if not f.is_available]
        
        # Check if any descriptions are AI-generated
        has_ai_descriptions = self.use_llm_descriptions
        
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
        
        # Add AI disclaimer if using LLM descriptions
        if has_ai_descriptions:
            if self.llm_calls_made >= self.max_llm_calls and len(features) > self.max_llm_calls:
                answer_parts.append(
                    f"\n<em style='color: #888; font-size: 0.9em;'>Note: AI-generated descriptions shown for first {self.max_llm_calls} feature(s) to prevent timeouts. Remaining features show manual extraction. All descriptions may contain inaccuracies.</em>"
                )
            else:
                answer_parts.append(
                    "\n<em style='color: #888; font-size: 0.9em;'>Note: Feature descriptions are AI-generated from sales manual content and may contain inaccuracies.</em>"
                )
        
        # Available features - organized by category
        if available:
            answer_parts.append("\n\n<strong>Currently Available:</strong>")
            
            # Group by category for better organization
            if categories['processor']:
                answer_parts.append("\n<em>Processor Activations:</em>")
                for feature in categories['processor']:
                    if feature.is_available:
                        # Clean up description - remove feature code if it's at the start
                        desc = feature.description
                        desc = re.sub(rf'^\(#{feature.feature_code}\)\s*[-:]?\s*', '', desc)
                        desc = re.sub(rf'^#{feature.feature_code}\s*[-:]?\s*', '', desc)
                        answer_parts.append(f"- <strong>#{feature.feature_code}</strong>: {desc}")
            
            if categories['memory']:
                answer_parts.append("\n<em>Memory Activations:</em>")
                for feature in categories['memory']:
                    if feature.is_available:
                        # Clean up description - remove feature code if it's at the start
                        desc = feature.description
                        desc = re.sub(rf'^\(#{feature.feature_code}\)\s*[-:]?\s*', '', desc)
                        desc = re.sub(rf'^#{feature.feature_code}\s*[-:]?\s*', '', desc)
                        answer_parts.append(f"- <strong>#{feature.feature_code}</strong>: {desc}")
            
            if categories['other']:
                answer_parts.append("\n<em>Other Activations:</em>")
                for feature in categories['other']:
                    if feature.is_available:
                        # Clean up description - remove feature code if it's at the start
                        desc = feature.description
                        desc = re.sub(rf'^\(#{feature.feature_code}\)\s*[-:]?\s*', '', desc)
                        desc = re.sub(rf'^#{feature.feature_code}\s*[-:]?\s*', '', desc)
                        answer_parts.append(f"- <strong>#{feature.feature_code}</strong>: {desc}")
        
        # Discontinued features
        if discontinued:
            answer_parts.append("\n\n<strong>Discontinued:</strong>")
            for feature in discontinued:
                # Clean up description - remove feature code if it's at the start
                desc = feature.description
                desc = re.sub(rf'^\(#{feature.feature_code}\)\s*[-:]?\s*', '', desc)
                desc = re.sub(rf'^#{feature.feature_code}\s*[-:]?\s*', '', desc)
                answer_parts.append(
                    f"- <strong>#{feature.feature_code}</strong>: {desc} "
                    f"<em>(No longer available as of {feature.discontinued_date})</em>"
                )
        
        return "\n".join(answer_parts)


# Convenience function
def extract_activation_features(chunks: List[Dict], max_llm_calls: int = 1) -> List[ActivationFeature]:
    """
    Quick extraction without creating service instance
    
    Args:
        chunks: List of chunk dictionaries
        max_llm_calls: Maximum number of LLM calls to prevent timeouts (default: 1)
    """
    service = ActivationFeatureService(max_llm_calls=max_llm_calls)
    return service.extract_features_from_chunks(chunks)


# Made with Bob