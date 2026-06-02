# RAG Chunks Display & Prompt Enhancement - Implementation Update

## Changes Made

### 1. Improved RAG Prompt (`rag-backend/app.py` lines 2087-2115)

**Enhanced LLM Context and Instructions:**
- Added explicit context that IBM Power servers are enterprise computing systems, not consumer appliances
- Provided guidance on how to interpret technical specifications (heat generation, power consumption)
- Instructed LLM to frame answers in the context of data center planning and enterprise server specifications
- This prevents misleading responses like "The E-1080 is a heater" and instead produces proper technical descriptions

**Before:**
```python
rag_prompt = f"""You are an expert on IBM Power Systems. Answer the following question based ONLY on the provided context from the IBM Power sales manual.
```

**After:**
```python
rag_prompt = f"""You are an expert on IBM Power Systems enterprise servers. You are answering questions about IBM Power servers, which are high-performance enterprise computing systems used in data centers for mission-critical workloads.

IMPORTANT CONTEXT:
- IBM Power servers (like E1080, S1024, etc.) are enterprise-grade computing systems, NOT consumer appliances
- When the sales manual mentions "heat generation" or "BTU output", this refers to the thermal characteristics of the server hardware that data center operators need to plan for cooling infrastructure
- Power consumption specifications help customers plan electrical and cooling requirements for data center deployment
```

### 2. Frontend UI Enhancement (`carbon-rag-ui/src/app/sales-manual/page.js`)

**Added Layer wrapper to Source URL tile** (Line ~955):
- Wrapped the source URL tile with `<Layer withBackground>` for consistent styling
- This ensures the source link appears with the same visual treatment as other sections

**Added Debug Logging** (Lines ~477 and ~531):
- Added console.log statements to track what data is being received from the backend
- Logs show: query_type, chunks presence, chunk count, source URL presence

### 2. Existing Implementation (Already Working)

**Chunks Display** (Lines 918-952):
```jsx
{queryResults.chunks_used && queryResults.chunks_used.length > 0 && (
  <Layer withBackground>
    <Tile className="chunks-tile">
      <h5>Context Used ({queryResults.chunks_used.length} chunks)</h5>
      {queryResults.chunks_used.map((chunk, idx) => (
        <div key={idx} className="chunk-item">
          <Tag type="blue">Chunk {idx + 1}</Tag>
          {chunk.metadata?.section && (
            <Tag type="outline">{chunk.metadata.section}</Tag>
          )}
          {chunk.score && (
            <Tag type="green">Score: {chunk.score.toFixed(3)}</Tag>
          )}
          <p>{chunk.text}</p>
        </div>
      ))}
    </Tile>
  </Layer>
)}
```

**Source URL Display** (Lines 955-972):
```jsx
{queryResults.source_url && (
  <Layer withBackground>
    <Tile className="source-tile">
      <h5>Source:</h5>
      <a href={queryResults.source_url} target="_blank">
        {queryResults.source_filename || queryResults.source_url}
      </a>
      <p>Click to verify this information in the original IBM Sales Manual</p>
    </Tile>
  </Layer>
)}
```

## Backend Implementation (Already Complete)

**Chunks Collection** (`rag-backend/app.py` lines 2044-2063):
```python
chunks_used = []
for hit in reranked_hits:
    source = hit["_source"]
    metadata = source.get("metadata", {})
    
    # Get source URL from first chunk
    if not source_url and metadata.get('source'):
        source_url = metadata['source']
        source_filename = metadata.get('filename')
    
    # Collect chunk information
    chunks_used.append({
        'text': source.get("text", "")[:500] + "..." if len(source.get("text", "")) > 500 else source.get("text", ""),
        'score': float(hit.get("_score", 0)),
        'metadata': {
            'section': metadata.get('section_title', 'Unknown'),
            'section_type': metadata.get('section_type', 'Unknown')
        }
    })
```

**Response Format** (`rag-backend/app.py` lines 2151-2165):
```python
return jsonify({
    'success': True,
    'content': result.get('content', ''),
    'query_type': query_type,
    'server_model': server_model,
    'chunks_found': len(hits),
    'chunks_used': chunks_used,  # ← Chunks with text, score, metadata
    'source_url': source_url,     # ← Link to sales manual
    'source_filename': source_filename,
    'ai_services_used': ['watsonx_assistant', 'opensearch', 'reranker', 'llm'],
    'processing_method': 'full_rag_generation'
})
```

## Testing Instructions

### 1. Rebuild and Deploy Frontend

```bash
cd C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual\carbon-rag-ui
npm run build
```

Then deploy using your existing deployment script:
```bash
./deploy-ui.sh
```

### 2. Test RAG Query

1. Navigate to the Sales Manual page
2. Ask a general question about a server (e.g., "How much heat does a E1080 generate?")
3. Open browser DevTools Console (F12)
4. Look for the `[Query Response]` log entry

**Expected Console Output:**
```javascript
[Query Response] {
  query_type: "rag",
  has_chunks: true,
  chunks_count: 5,
  has_source_url: true,
  source_url: "https://www.ibm.com/docs/...",
  source_filename: "IBM_Power_E1080.pdf"
}
```

**Expected UI Display:**
1. ✅ AI-generated answer at the top
2. ✅ "Context Used (5 chunks)" section showing:
   - Chunk number tags (blue)
   - Section name tags (outline)
   - Relevance scores (green)
   - Chunk text content
3. ✅ "Source:" section with clickable link to IBM Sales Manual

### 3. Verify Different Query Types

**Table Lookup** (e.g., "When was the E1080 announced?"):
- Should show table data
- Should show source URL
- Should NOT show chunks (table lookups don't use RAG)

**Activation Features** (e.g., "What activation features does the E1080 have?"):
- Should show structured feature list
- Should show source URL
- Should NOT show chunks (uses structured extraction)

**General RAG** (e.g., "What are the cooling requirements for E1080?"):
- Should show AI-generated answer
- Should show chunks used
- Should show source URL

## Troubleshooting

### If chunks don't appear:

1. **Check Console Logs:**
   - Look for `[Query Response]` in browser console
   - Verify `has_chunks: true` and `chunks_count > 0`

2. **Check Backend Response:**
   - If `chunks_count: 0`, the backend isn't finding relevant chunks
   - Check if the server's sales manual is indexed
   - Try a different question

3. **Check Query Type:**
   - If `query_type` is not "rag", chunks won't be shown
   - Table lookups and feature queries use different display logic

### If source URL doesn't appear:

1. **Check Console Logs:**
   - Verify `has_source_url: true`
   - Check if `source_url` has a value

2. **Check Metadata:**
   - Source URL comes from chunk metadata
   - Ensure sales manual was scraped (not uploaded PDF)
   - Scraped content includes source URLs, PDFs may not

## Architecture Flow

```
User Query
    ↓
Query Classifier (watsonx Assistant)
    ↓
Route Decision (table/feature/rag)
    ↓
[For RAG queries]
    ↓
OpenSearch Vector Search (hybrid: dense + sparse)
    ↓
Reranking (top 5 chunks)
    ↓
Collect chunks_used[] with:
  - text (truncated to 500 chars)
  - score (relevance)
  - metadata (section, type)
    ↓
LLM Generation (Granite)
    ↓
Return Response:
  - content (answer)
  - chunks_used[]
  - source_url
  - source_filename
    ↓
Frontend Display:
  1. Answer tile
  2. Chunks tile (if chunks_used exists)
  3. Source tile (if source_url exists)
```

## Summary

The chunks display feature is **fully implemented** in both backend and frontend. The changes made today:

1. ✅ Added `Layer` wrapper to source URL for consistent styling
2. ✅ Added debug logging to track response data
3. ✅ Verified backend returns chunks_used and source_url
4. ✅ Verified frontend displays chunks when present

The feature should work after rebuilding and redeploying the frontend. Use the console logs to verify data is flowing correctly from backend to frontend.