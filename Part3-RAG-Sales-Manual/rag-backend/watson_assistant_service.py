"""
Watson Assistant Integration Service
Provides enhanced NLP for query classification and entity extraction
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class WatsonAssistantService:
    """
    Watson Assistant service for enhanced query understanding
    Provides intent classification and entity extraction for IBM Power queries
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        assistant_id: Optional[str] = None,
        version: str = "2021-11-27"
    ):
        """
        Initialize Watson Assistant service
        
        Args:
            api_key: Watson Assistant API key
            url: Watson Assistant service URL
            assistant_id: Assistant ID (optional, can be set later)
            version: API version
        """
        self.api_key = api_key or os.environ.get('WATSON_ASSISTANT_API_KEY')
        self.url = url or os.environ.get('WATSON_ASSISTANT_URL')
        self.assistant_id = assistant_id or os.environ.get('WATSON_ASSISTANT_ID') or os.environ.get('WATSON_ASSISTANT_ASSISTANT_ID')
        self.version = version
        
        # Session management
        self.session_id = None
        self.session_created_at = None
        
        # Validate configuration
        if not self.api_key or not self.url:
            logger.warning("Watson Assistant not configured. API key or URL missing.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Watson Assistant service initialized at {self.url}")
    
    def is_enabled(self) -> bool:
        """Check if Watson Assistant is properly configured"""
        return self.enabled and self.api_key and self.url
    
    def _get_session(self) -> Optional[str]:
        """
        Get or create a Watson Assistant session
        Sessions expire after 5 minutes of inactivity
        """
        if not self.is_enabled() or not self.assistant_id:
            return None
        
        # Create new session if needed
        if not self.session_id:
            try:
                session_url = f"{self.url}/v2/assistants/{self.assistant_id}/sessions"
                response = requests.post(
                    session_url,
                    params={'version': self.version},
                    auth=('apikey', self.api_key),
                    timeout=10
                )
                response.raise_for_status()
                
                data = response.json()
                self.session_id = data.get('session_id')
                self.session_created_at = datetime.utcnow()
                
                logger.info(f"Created Watson Assistant session: {self.session_id}")
                
            except Exception as e:
                logger.error(f"Failed to create Watson Assistant session: {e}")
                return None
        
        return self.session_id
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query using Watson Assistant
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with intents, entities, and confidence scores
        """
        if not self.is_enabled():
            logger.warning("Watson Assistant not enabled, returning empty analysis")
            return {
                'success': False,
                'error': 'Watson Assistant not configured',
                'intents': [],
                'entities': []
            }
        
        session_id = self._get_session()
        if not session_id:
            return {
                'success': False,
                'error': 'Failed to create session',
                'intents': [],
                'entities': []
            }
        
        try:
            # Send message to Watson Assistant
            message_url = f"{self.url}/v2/assistants/{self.assistant_id}/sessions/{session_id}/message"
            
            payload = {
                'input': {
                    'message_type': 'text',
                    'text': query
                }
            }
            
            response = requests.post(
                message_url,
                params={'version': self.version},
                auth=('apikey', self.api_key),
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract intents and entities
            output = data.get('output', {})
            intents = output.get('intents', [])
            entities = output.get('entities', [])
            
            logger.info(f"Watson Assistant analysis: {len(intents)} intents, {len(entities)} entities")
            
            return {
                'success': True,
                'intents': intents,
                'entities': entities,
                'output': output,
                'raw_response': data
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Watson Assistant API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'intents': [],
                'entities': []
            }
        except Exception as e:
            logger.error(f"Error analyzing query with Watson Assistant: {e}")
            return {
                'success': False,
                'error': str(e),
                'intents': [],
                'entities': []
            }
    
    def extract_lifecycle_intent(self, analysis: Dict[str, Any]) -> Optional[str]:
        """
        Extract lifecycle-related intent from Watson Assistant analysis
        Works with the actual Watson Assistant entity format
        
        Returns:
            'announced', 'available', 'withdrawn', 'end_of_support', or None
        """
        if not analysis.get('success'):
            return None
        
        entities = analysis.get('entities', [])
        
        # Look for Lifecycle_date entity (your Watson uses this!)
        for entity in entities:
            if entity.get('entity') == 'Lifecycle_date':
                value = entity.get('value', '').lower()
                confidence = entity.get('confidence', 0)
                
                if confidence > 0.5:
                    # Map Watson's lifecycle values to our field names
                    lifecycle_mapping = {
                        'eos': 'end_of_support',
                        'end of support': 'end_of_support',
                        'announcement': 'announced',
                        'generally available': 'available',
                        'ga': 'available',
                        'withdrawal': 'withdrawn',
                        'eol': 'end_of_support',
                        'end of life': 'end_of_support'
                    }
                    
                    mapped_value = lifecycle_mapping.get(value)
                    if mapped_value:
                        logger.info(f"Extracted lifecycle field from Watson: {value} → {mapped_value}")
                        return mapped_value
        
        return None
    
    def extract_server_model(self, analysis: Dict[str, Any]) -> Optional[str]:
        """
        Extract server model from Watson Assistant entities
        Works with Server_Name entity from your Watson Assistant
        
        Returns:
            Server model string (e.g., "E1180", "S924") or None
        """
        if not analysis.get('success'):
            return None
        
        entities = analysis.get('entities', [])
        
        for entity in entities:
            entity_type = entity.get('entity', '')
            
            # Look for Server_Name entity (your Watson uses this!)
            if entity_type == 'Server_Name':
                value = entity.get('value', '')
                confidence = entity.get('confidence', 0)
                
                if confidence > 0.5 and value:
                    # Extract just the model number from full name
                    # "IBM Power System S924" → "S924"
                    # "IBM Power E1180" → "E1180"
                    import re
                    match = re.search(r'([ESHL]C?\d{3,4})', value, re.IGNORECASE)
                    if match:
                        model = match.group(1)
                        logger.info(f"Extracted server model from Watson: {value} → {model}")
                        return model
                    else:
                        logger.info(f"Extracted server name from Watson: {value}")
                        return value
        
        return None
    
    def extract_mtm(self, analysis: Dict[str, Any]) -> Optional[str]:
        """
        Extract MTM (Machine Type-Model) from Watson Assistant entities
        Works with Server_MTM entity from your Watson Assistant
        
        Returns:
            MTM string (e.g., "9080-HEU", "9009-42A") or None
        """
        if not analysis.get('success'):
            return None
        
        entities = analysis.get('entities', [])
        
        # Look for Server_MTM entity (your Watson uses this!)
        for entity in entities:
            entity_type = entity.get('entity', '')
            
            if entity_type == 'Server_MTM':
                value = entity.get('value', '')
                confidence = entity.get('confidence', 0)
                
                if confidence > 0.5 and value:
                    logger.info(f"Extracted MTM from Watson: {value}")
                    return value
        
        # Also check response text for MTM mentions
        # Your Watson says: "The Machine Type and Model for the IBM Power System S924 is 9009-42A"
        output = analysis.get('output', {})
        generic = output.get('generic', [])
        
        for item in generic:
            if item.get('response_type') == 'text':
                text = item.get('text', '')
                # Look for MTM pattern in response text
                import re
                match = re.search(r'(\d{4}-[A-Z0-9]{3})', text)
                if match:
                    mtm = match.group(1)
                    logger.info(f"Extracted MTM from Watson response text: {mtm}")
                    return mtm
        
        return None
    
    def extract_mtm_options(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract MTM options when Watson asks for clarification
        Your Watson may return multiple options when server name is ambiguous
        
        Returns:
            List of options with label and value (MTM)
            Example: [{'label': 'S924 (9009-42A)', 'value': '9009-42A'}, ...]
        """
        if not analysis.get('success'):
            return []
        
        output = analysis.get('output', {})
        generic = output.get('generic', [])
        
        options = []
        
        for item in generic:
            # Watson returns options when it needs clarification
            if item.get('response_type') == 'option':
                title = item.get('title', '')
                logger.info(f"Watson asking for clarification: {title}")
                
                for option in item.get('options', []):
                    label = option.get('label', '')
                    value = option.get('value', {})
                    
                    # Extract MTM from the option
                    import re
                    mtm_match = re.search(r'(\d{4}-[A-Z0-9]{3})', label)
                    if mtm_match:
                        mtm = mtm_match.group(1)
                        options.append({
                            'label': label,
                            'mtm': mtm,
                            'value': value
                        })
                        logger.info(f"Found MTM option: {label} → {mtm}")
        
        return options
    
    def needs_clarification(self, analysis: Dict[str, Any]) -> bool:
        """
        Check if Watson is asking for clarification (multiple MTM options)
        
        Returns:
            True if Watson returned options for user to choose from
        """
        if not analysis.get('success'):
            return False
        
        output = analysis.get('output', {})
        generic = output.get('generic', [])
        
        for item in generic:
            if item.get('response_type') == 'option':
                return True
        
        return False
    
    def get_query_classification(self, query: str) -> Dict[str, Any]:
        """
        Get comprehensive query classification using Watson Assistant
        Adapted for your actual Watson Assistant format
        Handles clarification requests when multiple MTMs exist
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with query_type, entities, confidence, needs_clarification, etc.
        """
        # Analyze with Watson Assistant
        analysis = self.analyze_query(query)
        
        if not analysis.get('success'):
            return {
                'success': False,
                'query_type': 'unknown',
                'confidence': 0.0,
                'entities': {},
                'watson_available': False,
                'needs_clarification': False
            }
        
        # Check if Watson is asking for clarification
        needs_clarification = self.needs_clarification(analysis)
        mtm_options = self.extract_mtm_options(analysis) if needs_clarification else []
        
        # Extract information
        intents = analysis.get('intents', [])
        entities = analysis.get('entities', [])
        
        # Determine query type based on YOUR Watson's intents
        query_type = 'rag'  # Default
        confidence = 0.0
        
        if intents:
            top_intent = intents[0]
            intent_name = top_intent.get('intent', '')
            confidence = top_intent.get('confidence', 0)
            
            # Your Watson uses "Check_Date" intent for lifecycle queries!
            if intent_name == 'Check_Date':
                query_type = 'table_lookup'
                logger.info(f"Watson detected Check_Date intent → TABLE_LOOKUP")
            elif intent_name == 'Technical_Question':
                # Could be metadata lookup or RAG
                query_type = 'rag'
        
        # Extract entities using your Watson's format
        extracted_entities = {
            'server_model': self.extract_server_model(analysis),
            'mtm': self.extract_mtm(analysis),
            'lifecycle_field': self.extract_lifecycle_intent(analysis)
        }
        
        # If Watson is asking for clarification, include the options
        if needs_clarification:
            logger.info(f"Watson needs clarification: {len(mtm_options)} options available")
            extracted_entities['mtm_options'] = mtm_options
        
        logger.info(f"Watson classification: type={query_type}, confidence={confidence:.3f}, entities={extracted_entities}, clarification={needs_clarification}")
        
        return {
            'success': True,
            'query_type': query_type,
            'confidence': confidence,
            'entities': extracted_entities,
            'intents': intents,
            'watson_entities': entities,
            'watson_available': True,
            'needs_clarification': needs_clarification,
            'mtm_options': mtm_options,
            'raw_analysis': analysis  # Include full analysis for debugging
        }
    
    def close_session(self):
        """Close the current Watson Assistant session"""
        if self.session_id and self.is_enabled():
            try:
                delete_url = f"{self.url}/v2/assistants/{self.assistant_id}/sessions/{self.session_id}"
                requests.delete(
                    delete_url,
                    params={'version': self.version},
                    auth=('apikey', self.api_key),
                    timeout=5
                )
                logger.info(f"Closed Watson Assistant session: {self.session_id}")
            except Exception as e:
                logger.warning(f"Failed to close Watson Assistant session: {e}")
            finally:
                self.session_id = None
                self.session_created_at = None


# Global instance (lazy loading)
_watson_assistant_service = None


def get_watson_assistant_service() -> WatsonAssistantService:
    """Get or create Watson Assistant service instance"""
    global _watson_assistant_service
    if _watson_assistant_service is None:
        _watson_assistant_service = WatsonAssistantService()
    return _watson_assistant_service


# Made with Bob