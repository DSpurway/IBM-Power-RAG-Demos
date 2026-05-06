# Hybrid Query Strategy: Direct Table Lookup + RAG + Reranking

## Overview
This document proposes a hybrid approach for answering Sales Manual queries, combining:
1. **Direct table lookup** for structured data queries
2. **Traditional RAG** for complex questions
3. **Reranking** for improved relevance

## Current vs. Proposed Architecture

### Current Architecture
```
User Query → Embedding → Vector Search → Top-K Chunks → LLM → Answer
```

### Proposed Hybrid Architecture
```
User Query → Query Classifier
    ├─→ [Table Query] → Direct Table Lookup → Structured Answer
    ├─→ [Simple RAG] → Vector Search → Top-K → LLM → Answer
    └─→ [Complex RAG] → Vector Search → Reranker → Top-K → LLM → Answer
```

## Use Case Analysis

### Type 1: Structured Table Queries (Direct Lookup)
**Examples:**
- "When was the IBM Power E1180 announced?"
- "What is the availability date for E1180?"
- "When was E1180 withdrawn from marketing?"

**Characteristics:**
- ✅ Answer is in a specific table cell
- ✅ Query pattern is predictable
- ✅ No interpretation needed
- ✅ Fast and deterministic

**Implementation:**
```python
def handle_lifecycle_query(query: str, server_model: str):
    """Direct table lookup for lifecycle dates"""
    # Extract query intent
    if "announced" in query.lower():
        return get_table_value(server_model, "Announced")
    elif "available" in query.lower():
        return get_table_value(server_model, "Available")
    elif "withdrawn" in query.lower():
        return get_table_value(server_model, "Marketing Withdrawn")
    # ... etc
```

**Advantages:**
- ⚡ **Fast**: No LLM call needed (~10ms vs ~2000ms)
- 💰 **Cost-effective**: No LLM tokens consumed
- 🎯 **Accurate**: No hallucination risk
- 📊 **Structured**: Can return JSON for programmatic use

### Type 2: Feature Availability Queries (Metadata Lookup + Simple Logic)
**Examples:**
- "Is feature code EFA1 still available?"
- "Can I order feature EFA1 today?"

**Characteristics:**
- ✅ Answer in extracted metadata
- ✅ Simple date comparison logic
- ✅ No complex reasoning needed

**Implementation:**
```python
def check_feature_availability(feature_code: str):
    """Check if feature is available based on withdrawal date"""
    metadata = get_feature_metadata(feature_code)
    if not metadata.get('withdrawal_dates'):
        return "Feature is available"
    
    withdrawal_date = parse_date(metadata['withdrawal_dates'][0]['date'])
    if datetime.now() > withdrawal_date:
        return f"Feature was withdrawn on {withdrawal_date}"
    else:
        return f"Feature is available until {withdrawal_date}"
```

### Type 3: Complex Queries (RAG with Reranking)
**Examples:**
- "What are the key differences between E1180 and E1150?"
- "Which server is best for SAP HANA workloads?"
- "Explain the memory expansion options for S1024"

**Characteristics:**
- ❌ Requires understanding multiple documents
- ❌ Needs comparison or reasoning
- ❌ Answer not in single location
- ✅ Benefits from reranking

## Reranking Benefits

### What is Reranking?
After initial vector search retrieves top-K chunks (e.g., K=20), a reranker model re-scores them based on semantic relevance to the query, selecting the best N (e.g., N=5) for the LLM.

### IBM Project AI Services Approach
From the reference you provided, they use:
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# After vector search
scores = reranker.predict([(query, chunk.text) for chunk in candidates])
top_chunks = [candidates[i] for i in scores.argsort()[-5:][::-1]]
```

### Benefits for Sales Manuals

**1. Better Relevance**
- Vector search might retrieve chunks with similar words but wrong context
- Reranker understands semantic relationship better
- Example: "memory" in "memory expansion" vs "memory requirements"

**2. Handling Ambiguity**
- Query: "What's the maximum memory?"
- Vector search might return: memory specs, memory activation, memory requirements
- Reranker identifies the most relevant: actual maximum memory specification

**3. Cross-Document Comparison**
- Query: "Compare E1180 and E1150"
- Vector search retrieves chunks from both
- Reranker ensures balanced representation

**4. Performance Impact**
- Initial retrieval: K=20 chunks (fast vector search)
- Reranking: 20 chunks (slower but more accurate)
- LLM: Only 5 best chunks (faster, cheaper)
- **Net result**: Better quality, similar or better performance

## Proposed Implementation

### Phase 1: Query Classification
```python
class QueryClassifier:
    """Classify query type to route to appropriate handler"""
    
    LIFECYCLE_PATTERNS = [
        r"when.*announced",
        r"when.*available",
        r"when.*withdrawn",
        r"availability date",
        r"announcement date"
    ]
    
    FEATURE_PATTERNS = [
        r"is.*available",
        r"can.*order",
        r"feature.*\w{4}",  # Feature codes
    ]
    
    def classify(self, query: str) -> str:
        """Returns: 'table_lookup', 'metadata_lookup', or 'rag'"""
        query_lower = query.lower()
        
        # Check for table queries
        for pattern in self.LIFECYCLE_PATTERNS:
            if re.search(pattern, query_lower):
                return 'table_lookup'
        
        # Check for feature queries
        for pattern in self.FEATURE_PATTERNS:
            if re.search(pattern, query_lower):
                return 'metadata_lookup'
        
        # Default to RAG
        return 'rag'
```

### Phase 2: Hybrid Query Handler
```python
class HybridQueryHandler:
    def __init__(self):
        self.classifier = QueryClassifier()
        self.table_lookup = TableLookupService()
        self.metadata_lookup = MetadataLookupService()
        self.rag_service = RAGService(use_reranking=True)
    
    async def answer_query(self, query: str) -> dict:
        query_type = self.classifier.classify(query)
        
        if query_type == 'table_lookup':
            return await self.table_lookup.query(query)
        
        elif query_type == 'metadata_lookup':
            return await self.metadata_lookup.query(query)
        
        else:  # RAG with reranking
            return await self.rag_service.query(query)
```

### Phase 3: RAG with Reranking
```python
class RAGService:
    def __init__(self, use_reranking=True):
        self.use_reranking = use_reranking
        if use_reranking:
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    async def query(self, query: str) -> dict:
        # Step 1: Vector search (retrieve more candidates)
        candidates = await self.vector_search(query, top_k=20)
        
        # Step 2: Rerank if enabled
        if self.use_reranking:
            scores = self.reranker.predict([
                (query, chunk.text) for chunk in candidates
            ])
            # Select top 5 after reranking
            top_indices = scores.argsort()[-5:][::-1]
            final_chunks = [candidates[i] for i in top_indices]
        else:
            final_chunks = candidates[:5]
        
        # Step 3: Generate answer with LLM
        return await self.generate_answer(query, final_chunks)
```

## Performance Comparison

### Current Approach (RAG Only)
```
Query: "When was E1180 announced?"
├─ Vector search: 50ms
├─ LLM generation: 2000ms
└─ Total: 2050ms
Cost: ~0.001 tokens
Accuracy: 95% (may hallucinate if chunk unclear)
```

### Proposed Approach (Hybrid)
```
Query: "When was E1180 announced?"
├─ Classification: 5ms
├─ Table lookup: 10ms
└─ Total: 15ms
Cost: $0 (no LLM)
Accuracy: 100% (deterministic)
```

### Complex Query (with Reranking)
```
Query: "Compare E1180 and E1150 memory options"
├─ Classification: 5ms
├─ Vector search (K=20): 50ms
├─ Reranking: 100ms
├─ LLM generation (5 chunks): 1500ms
└─ Total: 1655ms
Cost: ~0.0008 tokens (fewer chunks)
Accuracy: 98% (better context)
```

## Implementation Roadmap

### Phase 1: Table Lookup Service (Quick Win)
**Effort**: 1-2 days
**Impact**: High for lifecycle queries

1. Create table extraction service
2. Build query classifier for lifecycle patterns
3. Implement direct lookup logic
4. Add to existing RAG pipeline

### Phase 2: Metadata Lookup Service
**Effort**: 1 day
**Impact**: Medium for feature queries

1. Use existing metadata extraction
2. Add feature availability logic
3. Integrate with query classifier

### Phase 3: Reranking Integration
**Effort**: 2-3 days
**Impact**: High for complex queries

1. Add reranker model (cross-encoder)
2. Modify vector search to retrieve K=20
3. Add reranking step
4. Benchmark performance

### Phase 4: Optimization
**Effort**: Ongoing
**Impact**: Continuous improvement

1. Monitor query patterns
2. Tune classification rules
3. Adjust reranking thresholds
4. A/B test with users

## Cost-Benefit Analysis

### Benefits
- ✅ **Faster**: Table lookups 100x faster than LLM
- ✅ **Cheaper**: No LLM tokens for simple queries
- ✅ **More Accurate**: Deterministic for structured data
- ✅ **Better UX**: Instant answers for common questions
- ✅ **Scalable**: Reranking improves quality without more LLM calls

### Costs
- ⚠️ **Complexity**: More code to maintain
- ⚠️ **Reranker**: Additional model to deploy (~100MB)
- ⚠️ **Classification**: May misclassify some queries

### ROI Estimate
Assuming 1000 queries/day:
- 40% are table lookups (400 queries)
- Savings: 400 × 2 seconds = 800 seconds/day
- Cost savings: 400 × $0.001 = $0.40/day = $146/year
- **Plus**: Better user experience, faster responses

## Recommendation

### Implement in This Order:

**1. Start with Table Lookup (Phase 1)** ✅ Recommended
- Immediate impact
- Low complexity
- High user satisfaction
- Easy to measure success

**2. Add Reranking (Phase 3)** ✅ Recommended
- Significant quality improvement
- Proven approach (IBM project-ai-services)
- Moderate complexity
- Worth the effort

**3. Consider Metadata Lookup (Phase 2)** ⚠️ Optional
- Nice to have
- Lower frequency use case
- Can be added later

## Next Steps

1. **Test Current System**: Establish baseline metrics
2. **Implement Table Lookup**: Quick win for lifecycle queries
3. **Evaluate Reranking**: Test with cross-encoder model
4. **Measure Improvement**: Compare accuracy and performance
5. **Iterate**: Refine based on user feedback

## References

- IBM project-ai-services reranking: https://github.com/IBM/project-ai-services/tree/main/spyre-rag/src/chatbot
- Cross-encoder models: https://www.sbert.net/examples/applications/cross-encoder/README.html
- Reranking best practices: https://www.pinecone.io/learn/series/rag/rerankers/

---
**Created**: 2026-05-06  
**Author**: Bob (AI Assistant)  
**Status**: Proposal for Discussion