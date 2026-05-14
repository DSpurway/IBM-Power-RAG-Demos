# Part 2 Search Fix - Harry Potter Collection

## Problem
After implementing advanced query classification and hybrid search for Part 3 (Sales Manuals), Part 2 (Harry Potter) broke with a "status 500" error and "Failed to retrieve chunks" message.

## Root Cause
The search endpoint was enhanced to always use:
1. **Query Classification** - Designed to extract server models, MTMs, and lifecycle fields from queries
2. **Hybrid Search Mode** - Requires a hybrid pipeline in OpenSearch that may not exist for simple collections

For simple collections like Harry Potter:
- Query classification is unnecessary and could cause confusion
- Hybrid search mode may not be configured
- The collection doesn't have the complex metadata structure needed for advanced routing

## Solution
Modified `/api/search` endpoint in `app.py` to:

### 1. Detect Collection Type
```python
is_sales_manual_collection = 'sales_manual' in collection_name.lower() or collection_name.startswith('ibm_power_')
```

### 2. Skip Classification for Simple Collections
- For sales manual collections: Use full query classification with entity extraction
- For simple collections (like Harry Potter): Skip classification, use basic RAG mode

### 3. Use Dense Search for Simple Collections
- Sales manual collections: Default to hybrid search (more sophisticated)
- Simple collections: Default to dense (vector) search (more reliable, no pipeline required)

### 4. Add Fallback Error Handling
If hybrid search fails (e.g., pipeline not configured):
```python
try:
    # Try hybrid search
    response = client.search(index=index_name, body=search_body, params=params)
except Exception as search_error:
    if mode == "hybrid":
        # Fall back to dense search
        logger.warning(f"Hybrid search failed: {search_error}. Falling back to dense search.")
        # Execute dense search instead
```

## Changes Made

### File: `Part3-RAG-Sales-Manual/rag-backend/app.py`

**Lines 690-740**: Added collection type detection and conditional classification
- Detects if collection is a sales manual or simple collection
- Skips query classifier for simple collections
- Automatically switches to dense mode for simple collections

**Lines 843-895**: Added hybrid search fallback
- Wraps hybrid search in try-catch
- Falls back to dense search if hybrid fails
- Logs the fallback for debugging

## Benefits
1. **Backward Compatibility**: Part 2 (Harry Potter) works again
2. **Forward Compatibility**: Part 3 (Sales Manuals) retains all advanced features
3. **Robustness**: Graceful fallback if hybrid search is unavailable
4. **Flexibility**: System adapts to collection complexity automatically

## Testing
To verify the fix:

1. **Test Part 2 (Harry Potter)**:
   - Navigate to Part 2 in the UI
   - Ask a question about Harry Potter
   - Should retrieve chunks successfully without errors

2. **Test Part 3 (Sales Manuals)**:
   - Navigate to Part 3 in the UI
   - Ask about server lifecycle dates (e.g., "When was the E1180 announced?")
   - Should still use query classification and table lookup

3. **Check Logs**:
   - Simple collections should show: "Simple collection detected, skipping classification"
   - Sales manual collections should show: "Query classified as: table_lookup/rag/metadata_lookup"

## Future Considerations
- Could add a collection metadata field to explicitly mark collection type
- Could make search mode configurable per collection
- Could add UI toggle for search mode (dense/sparse/hybrid)

---
*Fixed: 2026-05-14*
*Issue: Part 2 search broken after Part 3 enhancements*
*Solution: Collection-aware search routing with graceful fallbacks*