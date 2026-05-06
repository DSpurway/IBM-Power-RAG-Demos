"""
Reranker Service for Improved RAG Relevance
Uses cross-encoder model to rerank retrieved chunks
Based on IBM project-ai-services approach
"""

import logging
import os
from typing import List, Dict, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    logger.warning("sentence-transformers not available. Reranking will be disabled.")


class RerankerService:
    """Service for reranking retrieved chunks using cross-encoder"""
    
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        Initialize reranker service
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.model = None
        self.enabled = RERANKER_AVAILABLE and os.environ.get('ENABLE_RERANKING', 'true').lower() == 'true'
        
        if self.enabled:
            try:
                logger.info(f"Loading reranker model: {model_name}")
                self.model = CrossEncoder(model_name)
                logger.info("Reranker model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load reranker model: {e}")
                self.enabled = False
        else:
            logger.info("Reranking disabled")
    
    def rerank(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Rerank chunks based on relevance to query
        
        Args:
            query: User query
            chunks: List of chunk dictionaries with 'text' field
            top_k: Number of top chunks to return
            
        Returns:
            List of top-k reranked chunks
        """
        if not self.enabled or not self.model:
            # Return original chunks if reranking disabled
            logger.debug("Reranking disabled, returning original chunks")
            return chunks[:top_k]
        
        if len(chunks) == 0:
            return []
        
        if len(chunks) <= top_k:
            # No need to rerank if we have fewer chunks than requested
            return chunks
        
        try:
            # Prepare query-chunk pairs
            pairs = [(query, chunk.get('text', '')) for chunk in chunks]
            
            # Get relevance scores
            logger.debug(f"Reranking {len(chunks)} chunks for query: {query[:50]}...")
            scores = self.model.predict(pairs)
            
            # Sort by score (descending)
            scored_chunks = list(zip(chunks, scores))
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            
            # Return top-k
            top_chunks = [chunk for chunk, score in scored_chunks[:top_k]]
            
            # Log reranking results
            top_scores = [score for _, score in scored_chunks[:top_k]]
            logger.info(f"Reranked {len(chunks)} chunks, top-{top_k} scores: {[f'{s:.3f}' for s in top_scores]}")
            
            # Add reranking scores to chunks for debugging
            for i, (chunk, score) in enumerate(scored_chunks[:top_k]):
                chunk['rerank_score'] = float(score)
                chunk['rerank_position'] = i + 1
            
            return top_chunks
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            # Fallback to original chunks
            return chunks[:top_k]
    
    def rerank_with_scores(self, query: str, chunks: List[Dict]) -> List[Tuple[Dict, float]]:
        """
        Rerank chunks and return with scores
        
        Args:
            query: User query
            chunks: List of chunk dictionaries
            
        Returns:
            List of (chunk, score) tuples sorted by score
        """
        if not self.enabled or not self.model:
            # Return with dummy scores
            return [(chunk, 0.0) for chunk in chunks]
        
        if len(chunks) == 0:
            return []
        
        try:
            # Prepare query-chunk pairs
            pairs = [(query, chunk.get('text', '')) for chunk in chunks]
            
            # Get relevance scores
            scores = self.model.predict(pairs)
            
            # Sort by score (descending)
            scored_chunks = list(zip(chunks, scores))
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            
            return scored_chunks
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            return [(chunk, 0.0) for chunk in chunks]
    
    def is_enabled(self) -> bool:
        """Check if reranking is enabled"""
        return self.enabled
    
    def get_model_info(self) -> Dict[str, any]:  # type: ignore
        """Get information about the reranker model"""
        return {
            'enabled': self.enabled,
            'model_name': self.model_name if self.enabled else None,
            'available': RERANKER_AVAILABLE
        }


# Singleton instance
_reranker_service = None


def get_reranker_service() -> RerankerService:
    """Get or create singleton reranker service"""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service


def rerank_chunks(query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
    """
    Convenience function for reranking chunks
    
    Args:
        query: User query
        chunks: List of chunk dictionaries
        top_k: Number of top chunks to return
        
    Returns:
        List of top-k reranked chunks
    """
    service = get_reranker_service()
    return service.rerank(query, chunks, top_k)


# Made with Bob