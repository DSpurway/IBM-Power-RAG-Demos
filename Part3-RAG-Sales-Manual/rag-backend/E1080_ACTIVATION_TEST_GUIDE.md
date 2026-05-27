# E1080 Activation Test Guide

## Overview

This test helps you understand exactly what happens when querying for activation features on the E1080 (MTM 9080-HEX). It shows the complete flow from retrieval to LLM processing to final output.

## What This Test Shows

### 1. **OpenSearch Retrieval**
- What chunks are retrieved from the vector database
- How many chunks match the activation query
- The similarity scores for each chunk
- Preview of the actual chunk text

### 2. **Activation Feature Extraction**
- Which feature codes are found (e.g., #EDAR, #ELCP)
- Manual extraction (without LLM)
- LLM-enhanced extraction (with AI descriptions)
- What text excerpt is sent to the LLM

### 3. **LLM Processing**
- The exact prompt sent to Granite LLM
- The excerpt from the sales manual used
- The AI-generated description returned
- Comparison with manual extraction

### 4. **Final Output**
- Formatted answer with all features
- Categorization (processor, memory, other)
- Availability status (available vs discontinued)
- Complete JSON results file

## Running the Test

### Quick Start

```powershell
cd Part3-RAG-Sales-Manual/rag-backend
./run-e1080-test.ps1
```

This will:
1. Find your rag-backend pod
2. Copy the test script to the pod
3. Run the test inside the pod
4. Show detailed output in your terminal
5. Copy the results JSON file back to your local machine

### Manual Run (if needed)

```powershell
# Find the pod
$pod = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}'

# Copy test script
oc cp test_e1080_activation_simple.py ${pod}:/app/

# Run test
oc exec $pod -- python test_e1080_activation_simple.py

# Copy results back
oc cp ${pod}:/app/e1080_activation_test_results.json ./e1080_activation_test_results.json
```

## Understanding the Output

### Section 1: OpenSearch Connection
```
Step 1: Connecting to OpenSearch...
✓ Connected to OpenSearch at opensearch-service:9200
```
Confirms connection to the vector database.

### Section 2: Finding E1080 Collection
```
Step 2: Finding E1080 collection...
✓ Found E1080 collection: rag_abc123def456
```
Shows which collection contains E1080 data.

### Section 3: Retrieved Chunks
```
Step 3: Searching for Activation Chunks
✓ Found 20 chunks from OpenSearch

Preview of retrieved chunks:
--- Chunk 1 (Score: 0.8234) ---
  1: (#EDAR) 1 core Base Proc Act (Pools 2.0) for #EDP4 any OS (from Static)
  2: Each occurrence of this feature will permanently activate...
  ...
```

**What to look for:**
- **Number of chunks**: Should be 10-20 for a good query
- **Scores**: Higher is better (0.7+ is good)
- **Content**: Should contain activation feature codes like #EDAR, #ELCP
- **Keywords**: Look for "activation", "processor", "memory"

### Section 4: Feature Extraction

#### Without LLM (Manual)
```
--- WITHOUT LLM (Manual Extraction) ---
✓ Extracted 15 features (manual extraction)

Feature 1:
  Code: #EDAR
  Description: 1 core Base Proc Act (Pools 2.0) for #EDP4 any OS (from Static)
  Status: Available
```

**What to look for:**
- Feature codes are correctly extracted
- Descriptions are from the sales manual title line
- Status shows if available or discontinued

#### With LLM (AI-Enhanced)
```
--- WITH LLM (AI-Enhanced Descriptions) ---
✓ Extracted 15 features (with LLM enhancement)

First Feature (LLM-enhanced):
  Code: #EDAR
  Description: Activates one processor core for Power10 systems
  Status: Available

Excerpt sent to LLM for #EDAR:
  (#EDAR) 1 core Base Proc Act (Pools 2.0) for #EDP4 any OS (from Static)
  Each occurrence of this feature will permanently activate...
  Attributes provided: 1 core
```

**What to look for:**
- **LLM description**: Should be clearer and more concise than manual
- **Excerpt**: Shows exactly what text was sent to the LLM
- **Prompt size**: Should be small (< 500 chars) to avoid timeouts

### Section 5: Final Output
```
Summary Statistics:
  Total Features: 15
  Available: 12
  Discontinued: 3
  By Category:
    - processor: 8
    - memory: 4
    - other: 3

Formatted Answer (first 500 chars):
I found 15 activation features: 12 currently available and 3 discontinued.

Currently Available:
Processor Activations:
- #EDAR: Activates one processor core for Power10 systems
- #ELCP: Activates two processor cores for Power10 systems
...
```

**What to look for:**
- Total count matches expectations
- Categories are correct (processor vs memory)
- Answer is well-formatted and readable

## Results JSON File

The test creates `e1080_activation_test_results.json` with:

```json
{
  "query": "What activation features are available for E1080?",
  "collection": "rag_abc123def456",
  "chunks_retrieved": 20,
  "features_found": 15,
  "summary": {
    "total": 15,
    "available": 12,
    "discontinued": 3,
    "by_category": {
      "processor": 8,
      "memory": 4,
      "other": 3
    }
  },
  "features": [
    {
      "feature_code": "EDAR",
      "description": "Activates one processor core...",
      "is_available": true,
      "status": "Available",
      "chunk_text": "Full sales manual text here..."
    }
  ],
  "sample_chunks": [...]
}
```

### Key Fields to Review

1. **chunks_retrieved**: How many chunks OpenSearch found
2. **features_found**: How many activation features were extracted
3. **features[].chunk_text**: The full sales manual text for each feature
4. **features[].description**: The extracted/generated description
5. **sample_chunks**: Preview of what was retrieved from OpenSearch

## Troubleshooting

### No Chunks Retrieved
```
✓ Found 0 chunks from OpenSearch
```
**Problem**: E1080 data not ingested or wrong collection
**Solution**: Check if E1080 was ingested, verify collection name

### No Features Extracted
```
✓ Found 20 chunks from OpenSearch
✓ Extracted 0 features (manual extraction)
```
**Problem**: Chunks don't contain activation features
**Solution**: Review chunk content, may need to re-ingest with better chunking

### LLM Timeout
```
Granite LLM timeout for EDAR - skipping
```
**Problem**: Granite service is slow or overloaded
**Solution**: Normal behavior, test limits to 1 LLM call to prevent timeouts

### Wrong Features Extracted
**Problem**: Extracting physical features instead of activations
**Solution**: Check that chunk titles contain "activation" or "act"

## What Each Component Does

### 1. Query Embedding
```python
query_vector = embeddings.embed_query(query)
```
Converts your text query into a 384-dimensional vector for similarity search.

### 2. Vector Search
```python
"knn": {
    "embedding": {
        "vector": query_vector,
        "k": 20
    }
}
```
Finds the 20 most similar chunks using vector similarity (cosine distance).

### 3. Keyword Boost
```python
"should": [
    {"match": {"text": "activation"}},
    {"match": {"text": "processor activation"}}
]
```
Boosts chunks that contain activation-related keywords.

### 4. Feature Extraction
```python
feature = self.extract_feature_from_chunk(chunk_text, metadata)
```
Parses each chunk to find:
- Feature code (e.g., #EDAR)
- Description (title line)
- Discontinued date (if any)

### 5. LLM Enhancement (Optional)
```python
llm_description = self._generate_llm_description(feature_code, chunk_text)
```
Sends a small excerpt to Granite LLM to generate a clearer description.

## Expected Results for E1080

For a properly ingested E1080 sales manual, you should see:

- **15-25 activation features** total
- **Processor activations**: 8-12 features (1-core, 2-core, etc.)
- **Memory activations**: 4-8 features (16GB, 32GB, 64GB, etc.)
- **Mix of available and discontinued** features
- **Clear descriptions** for each feature

## Next Steps

After running this test, you can:

1. **Review the JSON file** for complete details
2. **Compare manual vs LLM descriptions** to see the improvement
3. **Check chunk quality** to see if re-ingestion is needed
4. **Verify feature codes** against the actual sales manual
5. **Test other MTMs** by modifying the query

## Related Files

- `test_e1080_activation_simple.py` - The test script
- `run-e1080-test.ps1` - PowerShell runner
- `activation_feature_service.py` - The service being tested
- `app.py` - Main backend that uses this service

## Questions?

If you see unexpected results:
1. Check the chunk previews - do they contain activation features?
2. Review the feature extraction logic in `activation_feature_service.py`
3. Verify the LLM prompt is appropriate for your data
4. Check if the sales manual was chunked correctly during ingestion