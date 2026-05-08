# OpenSearch-Based Table Lookup Implementation

## Overview

This document describes the enhancement to the Table Lookup Service to query OpenSearch directly instead of using a hardcoded dictionary. This allows lifecycle queries to work for **any** IBM Power server that has sales manual data loaded into OpenSearch.

## Problem Statement

Previously, the `table_lookup_service.py` used a hardcoded dictionary (`LIFECYCLE_DATA`) with only 4 servers:
- E1180
- E1150
- E1080
- E1050

This meant lifecycle queries like "When did we stop supporting the S924?" would fail because S924 wasn't in the hardcoded list.

## Solution

The Table Lookup Service now:
1. **Queries OpenSearch** for lifecycle information from sales manual chunks
2. **Works for ANY server** that has sales manual data loaded
3. **Extracts dates and information** directly from the sales manual text
4. **No LLM generation needed** - returns factual data from the manuals

## Architecture

### Query Flow

```
User Query: "When did we stop supporting the S924?"
    ↓
Watson Assistant / Query Classifier
    ↓ (Classifies as TABLE_LOOKUP)
    ↓ (Extracts: server_model="S924", field="end_of_support")
    ↓
TableLookupService.lookup()
    ↓
OpenSearch Hybrid Search
    ↓ (Text match + Vector similarity)
    ↓
Extract lifecycle info from chunks
    ↓
Return formatted answer
```

### Key Components

#### 1. TableLookupService (table_lookup_service.py)

**Constructor:**
```python
def __init__(self, opensearch_client=None, embeddings=None, index_prefix='rag'):
```

**Main Method:**
```python
def lookup(self, server_model: str, field: Optional[str] = None, 
           collection_name: str = 'sales_manuals') -> Dict[str, Any]:
```

**Search Strategy:**
- Builds a targeted search query combining model name + lifecycle terms
- Uses hybrid search: text matching + vector similarity
- Retrieves top 10 chunks from sales manuals
- Extracts specific lifecycle information using regex patterns

#### 2. App.py Integration

**Initialization:**
```python
def get_table_lookup_service():
    """Lazy load table lookup service with OpenSearch backend"""
    global _table_lookup_service
    if _table_lookup_service is None:
        client = get_opensearch_client()
        embeddings = get_embeddings()
        _table_lookup_service = TableLookupService(
            opensearch_client=client,
            embeddings=embeddings,
            index_prefix=OPENSEARCH_DB_PREFIX
        )
    return _table_lookup_service
```

**Query Handler:**
```python
if classification['query_type'] == QueryType.TABLE_LOOKUP:
    table_service = get_table_lookup_service()
    result = table_service.lookup(
        server_model=classification['entities'].get('server_model'),
        field=classification['entities'].get('field'),
        collection_name=collection_name
    )
```

## Search Query Construction

The service builds intelligent search queries based on the lifecycle field:

| Field | Search Terms |
|-------|-------------|
| announced | "announced", "announcement" |
| available | "available", "availability", "general availability" |
| withdrawn | "withdrawn", "withdrawal", "marketing withdrawn", "end of marketing" |
| end_of_support | "discontinued", "end of support", "end of service", "support discontinued" |

Example: For "S924" + "end_of_support", the query becomes:
```
"S924 discontinued end of support end of service support discontinued"
```

## Information Extraction

The service uses regex patterns to extract dates and information:

1. **Date Pattern:** Matches formats like:
   - `2024-03-15`
   - `March 15, 2024`
   - `March 15 2024`

2. **Context Matching:** Looks for sentences containing:
   - The server model name
   - Lifecycle keywords
   - Date patterns

3. **Fallback:** If no specific date is found, returns the most relevant chunk text

## Example Queries

### Query 1: End of Support
```
Question: "When did we stop supporting the S924?"

Classification:
- Type: TABLE_LOOKUP
- Server: S924
- Field: end_of_support

OpenSearch Query: "S924 discontinued end of support end of service support discontinued"

Result: "Support for the IBM Power S924 ended on September 30, 2023."
```

### Query 2: Announcement Date
```
Question: "When was the E1180 announced?"

Classification:
- Type: TABLE_LOOKUP
- Server: E1180
- Field: announced

OpenSearch Query: "E1180 announced announcement"

Result: "The IBM Power E1180 was announced on July 8, 2025."
```

### Query 3: General Lifecycle
```
Question: "What is the lifecycle of the S1024?"

Classification:
- Type: TABLE_LOOKUP
- Server: S1024
- Field: None (general)

OpenSearch Query: "S1024 lifecycle announced available withdrawn discontinued"

Result: [Returns comprehensive lifecycle information from sales manual]
```

## Benefits

### 1. Scalability
- Works for **any server** with sales manual data in OpenSearch
- No need to maintain hardcoded dictionaries
- Automatically includes new servers when manuals are loaded

### 2. Accuracy
- Data comes directly from official IBM sales manuals
- No LLM hallucination risk
- Factual, verifiable information

### 3. Performance
- Fast OpenSearch queries (< 100ms typically)
- No LLM generation overhead
- Direct data retrieval

### 4. Maintainability
- Single source of truth (sales manuals in OpenSearch)
- No manual updates needed
- Consistent with RAG data

## Integration with Watson Assistant

Watson Assistant provides superior intent classification:

1. **Intent Detection:** Recognizes `Check_Date` intent with 98%+ confidence
2. **Entity Extraction:** Extracts `Server_Name`, `Lifecycle_date`, `Server_MTM`
3. **Clarification:** Handles ambiguous queries (e.g., multiple MTMs for one server)

Example Watson Response:
```json
{
  "intents": [{"intent": "Check_Date", "confidence": 0.98}],
  "entities": [
    {"entity": "Lifecycle_date", "value": "EoS"},
    {"entity": "Server_Name", "value": "IBM Power System S924"}
  ]
}
```

## Error Handling

The service handles various error cases:

1. **Server Not Found:** Returns error if no chunks found for the server
2. **Collection Missing:** Returns error if OpenSearch index doesn't exist
3. **No Date Found:** Returns the most relevant text chunk even without a specific date
4. **OpenSearch Errors:** Catches and logs connection/query errors

## Testing

To test the new implementation:

1. **Ensure sales manuals are loaded:**
   ```bash
   # Check if sales_manuals collection exists
   curl http://rag-backend/api/list-collections
   ```

2. **Test a lifecycle query:**
   ```bash
   curl -X POST http://rag-backend/api/search \
     -H "Content-Type: application/json" \
     -d '{
       "question": "When did we stop supporting the S924?",
       "collection_name": "sales_manuals"
     }'
   ```

3. **Check the response:**
   ```json
   {
     "success": true,
     "query_type": "table_lookup",
     "results": [{
       "content": "Support for the IBM Power S924 ended on September 30, 2023.",
       "metadata": {
         "source": "sales_manual",
         "server_model": "S924",
         "field": "end_of_support",
         "chunks_found": 5
       },
       "score": 1.0
     }]
   }
   ```

## Deployment

### Files Modified

1. **table_lookup_service.py** - Complete rewrite to use OpenSearch
2. **app.py** - Updated initialization and query handler

### Environment Variables

No new environment variables needed. Uses existing:
- `OPENSEARCH_HOST`
- `OPENSEARCH_PORT`
- `OPENSEARCH_USERNAME`
- `OPENSEARCH_PASSWORD`
- `OPENSEARCH_DB_PREFIX`

### Deployment Steps

1. Commit changes to Git
2. Push to GitHub
3. OpenShift will auto-build from Git
4. New pod will deploy with updated code
5. Test with lifecycle queries

## Future Enhancements

1. **Caching:** Cache frequently requested lifecycle data
2. **Metadata Enrichment:** Store extracted lifecycle dates as metadata during ingestion
3. **Multi-language:** Support lifecycle queries in multiple languages
4. **Confidence Scores:** Return confidence based on chunk relevance
5. **Source Citations:** Include page numbers and document references

## Conclusion

This enhancement transforms the Table Lookup Service from a limited hardcoded solution to a scalable, OpenSearch-powered system that can answer lifecycle questions about any IBM Power server with loaded sales manual data. It maintains the performance benefits of direct lookup while leveraging the comprehensive data in OpenSearch.

---

**Author:** Bob  
**Date:** 2026-05-08  
**Version:** 1.0