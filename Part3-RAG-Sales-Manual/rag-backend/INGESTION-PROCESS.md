# Enhanced Ingestion Process Documentation

## Overview

The RAG backend uses an **enhanced smart chunking process** for all server ingestions, whether triggered individually or via bulk ingestion. This document explains how the process works and how to clean and re-ingest data.

## Key Components

### 1. Smart Hierarchical Chunker (`sales_manual_chunker.py`)

The `SalesManualChunker` class provides intelligent chunking that:

- **Preserves lifecycle tables intact** - Critical for direct table lookup queries
- **Extracts feature codes with metadata** - Enables metadata-based search
- **Creates semantic chunks** - Optimized for RAG retrieval
- **Maintains document structure** - Preserves sections, headings, and hierarchy

### 2. Ingestion Endpoints

#### `/ingest-scraped-content` (Primary Endpoint)
- Receives scraped content from the scraper service
- Applies smart hierarchical chunking via `SalesManualChunker`
- Generates embeddings for each chunk
- Stores in OpenSearch with rich metadata
- **Used by both single and bulk ingestion**

#### `/api/ingest-sales-manual` (Wrapper Endpoint)
- Calls external scraper service
- Transforms scraper response
- Forwards to `/ingest-scraped-content`
- Used by bulk ingestion process

#### `/api/start-bulk-ingestion` (Bulk Trigger)
- Processes all 27 IBM Power servers
- Calls `/api/ingest-sales-manual` for each server
- Runs in background thread
- Tracks progress via `bulk_ingestion_state`

## Collection Naming

Collections are stored with **MD5-hashed index names**:

```
Collection Name: rag_mtm_9080_m9s
Index Name: rag_abc123def456... (MD5 hash)
```

This is handled by `_generate_index_name()`:
```python
def _generate_index_name(collection_name):
    hash_part = hashlib.md5(collection_name.encode()).hexdigest()
    return f"{OPENSEARCH_DB_PREFIX}_{hash_part}"
```

## Enhanced Chunking Features

### Lifecycle Table Preservation
```python
# Extracted as single chunk with section_type: 'lifecycle_table'
# Preserves Markdown table format for direct parsing
# Enables fast, accurate responses without LLM
```

### Feature Code Extraction
```python
# Each feature code becomes a separate chunk
# Metadata includes: feature_code, description, section
# Enables metadata-based search and filtering
```

### Semantic Chunking
```python
# Sections chunked with overlap for context
# Metadata includes: section_title, section_type, hierarchy
# Optimized for RAG retrieval
```

## Cleaning and Re-ingestion Process

### Step 1: Clean All Collections

Use the provided script to delete all existing collections:

```bash
cd /path/to/rag-backend
./clean-all-collections.sh
```

The script will:
1. List all RAG collections (with hashed names)
2. Show document counts
3. Ask for confirmation
4. Delete all collections
5. Verify cleanup

### Step 2: Verify Cleanup

Check that all collections are deleted:

```bash
POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
oc exec $POD -- python -c "from opensearchpy import OpenSearch; c=OpenSearch([{'host':'opensearch-service','port':9200}],use_ssl=False); print(list(c.indices.get_alias(index='rag_*').keys()))"
```

Should return: `[]` (empty list)

### Step 3: Re-ingest Data

#### Option A: Bulk Ingestion (All Servers)
Trigger from the frontend UI:
- Navigate to the application
- Click "Bulk Ingest All Servers" (or equivalent button)
- Monitor progress in the UI

#### Option B: Single Server Test
Test with E980 first:
```bash
cd /path/to/rag-backend
./test-e980-ingestion.sh
```

### Step 4: Monitor Progress

Watch backend logs:
```bash
POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
oc logs -f $POD
```

Check bulk ingestion status:
```bash
curl -k https://$(oc get route rag-backend -o jsonpath='{.spec.host}')/api/bulk-ingestion-status
```

## Verification

### Check Collection Exists
```bash
POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
oc exec $POD -- python -c "from opensearchpy import OpenSearch; c=OpenSearch([{'host':'opensearch-service','port':9200}],use_ssl=False); print(c.count(index='rag_*'))"
```

### Verify Lifecycle Table
```bash
oc exec $POD -- python -c "from opensearchpy import OpenSearch; c=OpenSearch([{'host':'opensearch-service','port':9200}],use_ssl=False); r=c.search(index='rag_*',body={'query':{'match':{'metadata.section_type':'lifecycle_table'}},'size':1}); print(r['hits']['hits'][0]['_source']['text'][:500] if r['hits']['hits'] else 'Not found')"
```

### Check Chunk Distribution
Look for log entries like:
```
Chunk distribution: {'lifecycle_table': 1, 'feature_code': 45, 'section': 23}
```

## Server List (27 Servers)

The bulk ingestion processes these servers in order:

**POWER11:**
- E1180 (9080-HEU)
- E1150 (9043-MRU)
- S1124 (9824-42A)
- S1122 (9824-22A)

**POWER10:**
- E1080 (9080-HEX)
- E1050 (9043-MRX)
- S1024 (9105-42A)
- S1022 (9105-22A)
- S1014 (9105-41B)
- S1012 (9028-21B)
- L1024 (9786-42H)
- L1022 (9786-22H)

**POWER9:**
- E980 (9080-M9S)
- E950 (9040-MR9)
- S924 (9009-42A, 9009-42G)
- S922 (9009-22A, 9009-22G)
- S914 (9009-41A, 9009-41G)
- H924 (9223-42S)
- H922 (9223-22S)
- IC922 (9183-22X)
- L922 (9008-22L)
- LC922 (9006-22P)
- LC921 (9006-12P)

## Troubleshooting

### Scraper Not Accessible
```bash
# Check scraper URL in environment
oc get deployment rag-backend -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="SCRAPER_URL")].value}'

# Test scraper health
curl -s http://scraper-url/health
```

### Ingestion Timeout
- Default timeout: 15 minutes (900 seconds)
- Increase if needed in `app.py` line 2111

### Collection Not Found
- Verify collection name format: `rag_mtm_9080_m9s`
- Check index exists with hashed name
- Ensure ingestion completed successfully

### Old Data Contamination
- Use `clean-all-collections.sh` to remove all data
- Re-ingest from scratch
- Verify cleanup before re-ingestion

## Benefits of Enhanced Process

1. **Accurate Table Lookups** - Lifecycle tables preserved intact
2. **Fast Responses** - No LLM needed for table queries
3. **Better Context** - Hierarchical structure maintained
4. **Feature Search** - Metadata-based feature code search
5. **Consistent Quality** - Same process for all servers
6. **Change Detection** - Content hash tracking

## Made with Bob