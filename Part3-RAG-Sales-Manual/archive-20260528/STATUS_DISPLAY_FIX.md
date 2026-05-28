# Server Status Display Fix

## Problem
The UI was showing "Not Indexed" for all servers even though many (or all) servers had been successfully indexed during bulk ingestion. The status display was misleading and didn't reflect the actual state of the OpenSearch indices.

## Root Cause
The backend's `/api/collections` endpoint was checking if expected index names existed in OpenSearch, but it wasn't verifying that those indices actually contained documents. An empty index would be counted as "indexed" even though it had no data.

Additionally, the frontend wasn't displaying document counts, making it impossible to verify if servers were truly indexed.

## Important Note
The fix specifically targets **Sales Manual collections only** (MTM-based indices for IBM Power servers). Other collections like the Harry Potter demo collection are intentionally excluded from the Sales Manual status display, as they're used in earlier, more basic parts of the demo and should remain separate.

## Solution

### Backend Changes (`rag-backend/app.py`)
Enhanced the `list_collections()` function to:

1. **Check document counts**: For each matched index, query OpenSearch to get the actual document count
2. **Filter empty indices**: Only include indices that have `doc_count > 0` in the response
3. **Return detailed information**: Added `collections_details` to the response containing:
   - `index_name`: The hashed OpenSearch index name
   - `document_count`: Actual number of documents in the index
   - `collection_name`: The MTM-based collection name

**Key Code Change:**
```python
# Get document count for this index
count_response = client.count(index=expected_index)
doc_count = count_response.get('count', 0)

# Only include if it has documents
if doc_count > 0:
    collections_map[mtm] = expected_index
    collections_details[mtm] = {
        'index_name': expected_index,
        'document_count': doc_count,
        'collection_name': collection_name
    }
```

### Frontend Changes (`carbon-rag-ui/src/app/sales-manual/page.js`)
Updated the `loadServerStatus()` function to:

1. **Use document counts**: Extract `collections_details` from the API response
2. **Display actual counts**: Show real document counts in the "Docs" column instead of "?"
3. **Enhanced status messages**: Include total document count in status messages
4. **Better logging**: Log detailed information about indexed servers and document counts

**Key Code Change:**
```javascript
const collectionsDetails = data.collections_details || {};
const details = collectionsDetails[server.mtm];

return {
  ...server,
  documentCount: details ? details.document_count : 0
};
```

## Benefits

1. **Accurate Status**: UI now shows the true indexing status based on actual document counts
2. **Transparency**: Users can see exactly how many documents are indexed for each server
3. **Verification**: Easy to verify that bulk ingestion completed successfully
4. **Debugging**: Document counts help identify issues with specific servers

## Deployment

Run the deployment script from the workspace root:

```powershell
.\Part3-RAG-Sales-Manual\deploy-status-fix.ps1
```

This will:
1. Rebuild and deploy the backend with the enhanced status checking
2. Rebuild and deploy the frontend with the updated display logic
3. Show the URLs for both services

## Testing

After deployment:

1. **Open the UI**: Navigate to the Sales Manual page
2. **Click "Refresh Status"**: The status should now accurately reflect indexed servers
3. **Check the "Docs" column**: Should show actual document counts (not "?" or "0")
4. **Verify the status message**: Should show something like:
   - "26 servers indexed (1,234 documents)" if all are indexed
   - "15 servers indexed (678 documents), 11 not indexed" if partial

## API Response Format

The `/api/collections` endpoint now returns:

```json
{
  "success": true,
  "collections": ["opensearch_mtm_9080_heu_abc123", "opensearch_harry_potter_xyz789", ...],
  "sales_manual_collections": ["opensearch_mtm_9080_heu_abc123", ...],
  "other_collections": ["opensearch_harry_potter_xyz789", ...],
  "collections_map": {
    "9080-HEU": "opensearch_mtm_9080_heu_abc123",
    "9043-MRU": "opensearch_mtm_9043_mru_def456",
    ...
  },
  "collections_details": {
    "9080-HEU": {
      "index_name": "opensearch_mtm_9080_heu_abc123",
      "document_count": 47,
      "collection_name": "mtm_9080_heu"
    },
    "9043-MRU": {
      "index_name": "opensearch_mtm_9043_mru_def456",
      "document_count": 52,
      "collection_name": "mtm_9043_mru"
    },
    ...
  }
}
```

**Note:**
- `collections`: All indices (backward compatible, includes Harry Potter)
- `sales_manual_collections`: Only Sales Manual MTM-based indices
- `other_collections`: Non-Sales Manual indices (e.g., Harry Potter)
- `collections_map` and `collections_details`: Only contain Sales Manual servers

## Files Modified

1. `Part3-RAG-Sales-Manual/rag-backend/app.py` - Enhanced `list_collections()` function
2. `Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/page.js` - Updated `loadServerStatus()` function
3. `Part3-RAG-Sales-Manual/deploy-status-fix.ps1` - New deployment script (created)
4. `Part3-RAG-Sales-Manual/STATUS_DISPLAY_FIX.md` - This documentation (created)

## Notes

- The fix is backward compatible - existing functionality is preserved
- Empty indices are now correctly excluded from the "indexed" count
- The document count provides a quick sanity check for successful ingestion
- Typical document counts per server range from 30-60 depending on the Sales Manual content

---
*Made with Bob - 2026-05-12*