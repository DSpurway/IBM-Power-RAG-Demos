# Smart Chunking Deployment Guide

## Overview

This guide covers deploying the new smart hierarchical chunking system for IBM Sales Manuals. The new chunker creates semantically meaningful chunks that preserve table structure and enable the hybrid query system.

## What Changed

### Before (Old System)
- **1 massive chunk per server** (~5MB)
- Entire Sales Manual stored as single document
- Inefficient retrieval and slow queries
- Table structure lost in plain text

### After (New System)
- **~220-320 chunks per server** (~500-1500 chars each)
- Lifecycle table preserved as Markdown (1 chunk)
- Feature codes with metadata (200-300 chunks)
- Semantic sections for RAG (20-30 chunks)
- Fast, accurate hybrid queries

## Files Added/Modified

### New Files
- `sales_manual_chunker.py` - Smart hierarchical chunker

### Modified Files
- `app.py` - Updated `/ingest-scraped-content` endpoint

## Deployment Steps

### 1. Deploy Updated Backend

```powershell
# Navigate to backend directory
cd Part3-RAG-Sales-Manual/rag-backend

# Build and push new image
docker build -t rag-backend:smart-chunking .

# Tag for your registry
docker tag rag-backend:smart-chunking <your-registry>/rag-backend:smart-chunking

# Push to registry
docker push <your-registry>/rag-backend:smart-chunking

# Update deployment
oc set image deployment/rag-backend rag-backend=<your-registry>/rag-backend:smart-chunking -n llm-on-techzone

# Wait for rollout
oc rollout status deployment/rag-backend -n llm-on-techzone
```

### 2. Verify Deployment

```powershell
# Check pod status
oc get pods -n llm-on-techzone | Select-String "rag-backend"

# Check logs for successful startup
oc logs deployment/rag-backend -n llm-on-techzone --tail=50
```

### 3. Clear Existing Data (Optional but Recommended)

To get clean data with the new chunking strategy:

```powershell
# List current collections
curl http://<rag-backend-url>/api/collections

# Drop all existing collections (if desired)
# This will remove old 5MB chunks and allow fresh ingestion
# Note: You can also keep old data and just add new collections
```

### 4. Re-Ingest All Servers

Use the UI to trigger bulk ingestion:

1. Navigate to Sales Manual page
2. Click "Load All Documents" button
3. Monitor progress (will take several hours for 26 servers)

Or use API directly:

```powershell
# Trigger bulk ingestion
curl -X POST http://<rag-backend-url>/api/start-bulk-ingestion

# Monitor status
curl http://<rag-backend-url>/api/bulk-ingestion-status
```

### 5. Verify New Chunks

After ingestion completes, verify the chunking worked:

```powershell
# Check a specific server's chunks
curl "http://<rag-backend-url>/api/search" `
  -H "Content-Type: application/json" `
  -d '{
    "question": "Product lifecycle dates",
    "collection_name": "mtm_9009_42a",
    "k": 5
  }'
```

Expected results:
- Should return lifecycle table chunk (~500 chars)
- Metadata should show `section_type: "lifecycle_table"`
- Table should be in Markdown format with `|` separators

## Testing the Hybrid System

### Test 1: Direct Table Lookup (No LLM)
```
Question: "When did we stop selling S924?"
Expected: Fast response (~10ms) with lifecycle dates from table
```

### Test 2: Metadata Search (No LLM)
```
Question: "Which features were withdrawn in 2021?"
Expected: List of feature codes with withdrawal dates
```

### Test 3: Full RAG (With LLM)
```
Question: "What are the key differences between S924 and S922?"
Expected: Synthesized answer from multiple chunks
```

## Monitoring

### Check Chunk Distribution

After ingesting a server, check the logs:

```powershell
oc logs deployment/rag-backend -n llm-on-techzone | Select-String "Chunk distribution"
```

Expected output:
```
Chunk distribution: {
  'lifecycle_table': 1,
  'feature_code': 250,
  'content_section': 25
}
```

### Verify Table Preservation

Check that lifecycle table is properly formatted:

```powershell
# Query for lifecycle table
curl "http://<rag-backend-url>/api/search" `
  -H "Content-Type: application/json" `
  -d '{
    "question": "lifecycle dates",
    "collection_name": "mtm_9009_42a",
    "k": 1
  }' | jq '.results[0].content'
```

Should see Markdown table with `|` separators.

## Rollback Plan

If issues occur, rollback to previous version:

```powershell
# Rollback deployment
oc rollout undo deployment/rag-backend -n llm-on-techzone

# Verify rollback
oc rollout status deployment/rag-backend -n llm-on-techzone
```

## Performance Expectations

### Ingestion Time
- **Per server**: 5-10 minutes (unchanged)
- **All 26 servers**: 2-4 hours (unchanged)

### Query Performance
- **Direct table lookup**: ~10ms (10x faster)
- **Metadata search**: ~50ms (5x faster)
- **Full RAG**: ~2-5s (similar, but better quality)

### Storage
- **Per server**: ~220-320 chunks vs 1 chunk
- **Total storage**: Similar (chunks are smaller but more numerous)

## Troubleshooting

### Issue: No lifecycle table found
**Symptom**: Log shows "No lifecycle table found for MTM"
**Solution**: Check that scraper is returning full_text with lifecycle section

### Issue: No feature codes extracted
**Symptom**: Chunk distribution shows 0 feature_code chunks
**Solution**: Verify feature code pattern matches Sales Manual format

### Issue: Import error for sales_manual_chunker
**Symptom**: "ModuleNotFoundError: No module named 'sales_manual_chunker'"
**Solution**: Ensure sales_manual_chunker.py is in the Docker image

## Success Criteria

✅ Lifecycle table queries return in <50ms
✅ Table structure preserved (Markdown format with `|`)
✅ Feature codes have withdrawal_date metadata
✅ ~220-320 chunks per server
✅ All 26 servers successfully ingested

## Next Steps

After successful deployment:

1. Test all query types (table lookup, metadata search, full RAG)
2. Monitor query performance and accuracy
3. Gather user feedback on response quality
4. Consider adding more metadata fields (CSU, min/max values, etc.)

## Made with Bob