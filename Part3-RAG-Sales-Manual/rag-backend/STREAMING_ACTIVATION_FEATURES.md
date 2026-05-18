# Streaming Activation Features - Progressive Display

## Goal

Stream activation features to the UI as they're extracted, so users see:
1. Feature #1 appears after ~11 seconds (with LLM description)
2. Features #2-10 appear quickly (manual extraction)
3. No timeout because UI receives data progressively
4. Users can compare LLM vs manual in detail view

## Current Flow (Blocking)

```
Backend: Extract all 10 features → Wait for all → Send response
UI: Wait... wait... wait... → 504 timeout
```

## Desired Flow (Streaming)

```
Backend: Extract feature #1 → Stream to UI → Extract feature #2 → Stream to UI → ...
UI: Show feature #1 → Show feature #2 → Show feature #3 → ...
```

## Implementation Options

### Option 1: Server-Sent Events (SSE) - Recommended

**Backend:**
```python
from flask import Response, stream_with_context
import json

@app.route('/api/search/stream', methods=['POST'])
def search_stream():
    """Stream activation features as they're extracted"""
    
    def generate():
        # ... setup code ...
        
        # Stream features as they're extracted
        for i, chunk in enumerate(chunks):
            feature = activation_service.extract_feature_from_chunk(
                chunk['text'], 
                chunk['metadata']
            )
            
            if feature:
                # Send feature immediately
                yield f"data: {json.dumps(feature.to_dict())}\n\n"
        
        # Send completion signal
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )
```

**Frontend:**
```typescript
const eventSource = new EventSource('/api/search/stream');
const features: ActivationFeature[] = [];

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.done) {
    eventSource.close();
  } else {
    features.push(data);
    setFeatures([...features]); // Trigger re-render
  }
};
```

### Option 2: Chunked JSON Response

**Backend:**
```python
@app.route('/api/search/chunked', methods=['POST'])
def search_chunked():
    """Send features as newline-delimited JSON"""
    
    def generate():
        for i, chunk in enumerate(chunks):
            feature = activation_service.extract_feature_from_chunk(
                chunk['text'],
                chunk['metadata']
            )
            
            if feature:
                yield json.dumps(feature.to_dict()) + '\n'
    
    return Response(generate(), mimetype='application/x-ndjson')
```

**Frontend:**
```typescript
const response = await fetch('/api/search/chunked', {
  method: 'POST',
  body: JSON.stringify({ question, collection_name })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (line.trim()) {
      const feature = JSON.parse(line);
      setFeatures(prev => [...prev, feature]);
    }
  }
}
```

### Option 3: Modified Extraction with Callbacks

Modify `extract_features_from_chunks` to accept a callback:

```python
def extract_features_from_chunks(
    self, 
    chunks: List[Dict],
    on_feature_extracted: Optional[Callable[[ActivationFeature], None]] = None
) -> List[ActivationFeature]:
    """
    Extract features with optional callback for each feature
    """
    features = []
    seen_codes = set()
    self.llm_calls_made = 0
    
    for i, chunk in enumerate(chunks):
        feature = self.extract_feature_from_chunk(
            chunk['text'],
            chunk['metadata']
        )
        
        if feature and feature.feature_code not in seen_codes:
            features.append(feature)
            seen_codes.add(feature.feature_code)
            
            # Call callback immediately after extraction
            if on_feature_extracted:
                on_feature_extracted(feature)
    
    return features
```

## Recommended Approach: SSE with Modified Extraction

### Step 1: Modify Extraction Service

**File:** `activation_feature_service.py`

Add streaming support:

```python
def extract_features_from_chunks_streaming(
    self,
    chunks: List[Dict],
    yield_callback: Callable[[ActivationFeature], None]
) -> None:
    """
    Extract features and yield each one immediately via callback
    """
    seen_codes = set()
    self.llm_calls_made = 0
    
    logger.info(f"Streaming extraction: {len(chunks)} chunks, max {self.max_llm_calls} LLM calls")
    
    for i, chunk in enumerate(chunks):
        chunk_text = chunk.get('text', '')
        metadata = chunk.get('metadata', {})
        
        # Check for duplicate before extraction
        feature_match = self.FEATURE_CODE_PATTERN.search(chunk_text[:500])
        if feature_match and feature_match.group(1) in seen_codes:
            continue
        
        # Extract feature
        feature = self.extract_feature_from_chunk(chunk_text, metadata)
        
        if feature and feature.feature_code not in seen_codes:
            seen_codes.add(feature.feature_code)
            logger.info(f"Streaming feature {len(seen_codes)}: {feature.feature_code}")
            
            # Yield immediately
            yield_callback(feature)
    
    logger.info(f"Streaming complete: {len(seen_codes)} features, {self.llm_calls_made} LLM calls")
```

### Step 2: Add Streaming Endpoint

**File:** `app.py`

```python
@app.route('/api/search/activation/stream', methods=['POST'])
def search_activation_stream():
    """
    Stream activation features as they're extracted
    Avoids timeout by sending features progressively
    """
    try:
        data = request.get_json()
        question = data.get('question')
        collection_name = data.get('collection_name', 'sales_manuals')
        
        if not question:
            return jsonify({'error': 'question is required'}), 400
        
        def generate():
            # Setup (same as regular search)
            embeddings = get_embeddings()
            client = get_opensearch_client()
            index_name = _generate_index_name(collection_name)
            
            # Vector search for activation chunks
            query_vector = embeddings.embed_query(question)
            search_body = {
                "size": 20,
                "_source": ["chunk_id", "text", "metadata"],
                "query": {
                    "bool": {
                        "must": [{"knn": {"embedding": {"vector": query_vector, "k": 20}}}],
                        "should": [
                            {"match": {"text": "activation"}},
                            {"match": {"text": "activations"}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            
            response = client.search(index=index_name, body=search_body)
            hits = response['hits']['hits']
            
            logger.info(f"Streaming {len(hits)} activation chunks")
            
            # Extract and stream features
            activation_service = ActivationFeatureService(max_llm_calls=10)  # Allow more LLM calls
            chunks = [{'text': hit['_source']['text'], 'metadata': hit['_source'].get('metadata', {})}
                     for hit in hits]
            
            def yield_feature(feature: ActivationFeature):
                """Callback to stream each feature"""
                yield f"data: {json.dumps(feature.to_dict())}\n\n"
            
            # Stream features as they're extracted
            activation_service.extract_features_from_chunks_streaming(chunks, yield_feature)
            
            # Send completion signal
            yield f"data: {json.dumps({'done': True})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        return jsonify({'error': str(e)}), 500
```

### Step 3: Update Frontend

```typescript
// Use EventSource for SSE
const streamActivationFeatures = (question: string, collectionName: string) => {
  const features: ActivationFeature[] = [];
  
  const eventSource = new EventSource(
    `/api/search/activation/stream?question=${encodeURIComponent(question)}&collection_name=${collectionName}`
  );
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.done) {
      eventSource.close();
      console.log('Streaming complete');
    } else {
      // New feature received - update UI immediately
      features.push(data);
      setFeatures([...features]);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('Stream error:', error);
    eventSource.close();
  };
};
```

## Benefits

1. **No Timeout** - UI receives data progressively
2. **Better UX** - Users see results appearing
3. **LLM Evaluation** - Can compare LLM vs manual descriptions
4. **Flexible** - Can increase `max_llm_calls` without timeout risk

## Testing

```powershell
# Test streaming endpoint
curl -N "https://$BACKEND_URL/api/search/activation/stream" \
  -H "Content-Type: application/json" \
  -d '{"question":"What activations are available?","collection_name":"rag_36d5fcdd8f17c37ef0f739637cde0718"}'
```

You should see features appearing one by one in the response.

## Decision Point

With streaming, you can:
- **Increase `max_llm_calls`** to 5-10 (no timeout risk)
- **Compare LLM vs manual** in detail view
- **Decide later** whether LLM adds value

The side-by-side view will make it obvious if Granite is helping or just echoing.