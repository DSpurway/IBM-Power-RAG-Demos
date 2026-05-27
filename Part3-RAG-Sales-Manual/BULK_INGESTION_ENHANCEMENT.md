# Bulk Ingestion Enhancement - Intelligent Skip Logic

## Overview

The bulk ingestion process has been enhanced with **intelligent skip logic** that prevents unnecessary re-ingestion of unchanged Sales Manual content. This significantly reduces processing time and scraper load.

## Key Features

### 1. **Smart Change Detection**
- Calculates SHA-256 hash of source document content
- Compares with stored hash in OpenSearch metadata
- Only re-ingests if content has actually changed

### 2. **Collection Existence Check**
- Verifies if MTM-based collection already exists
- Checks document count to ensure collection is populated
- Skips empty or missing collections for re-ingestion

### 3. **Force Re-ingestion Option**
- Supports `force=true` parameter to override skip logic
- Useful for testing or when you know content needs refresh
- Default is `force=false` (intelligent skip enabled)

## How It Works

### Normal Mode (Intelligent Skip)
```bash
# POST to /api/start-bulk-ingestion
# No body needed, or {"force": false}
```

**Process:**
1. For each server, check if collection exists with documents
2. If exists, scrape current content and calculate hash
3. Compare new hash with stored hash in OpenSearch
4. **Skip if unchanged**, **re-ingest if changed**
5. Track skipped servers separately from completed/failed

### Force Mode (Re-ingest All)
```bash
# POST to /api/start-bulk-ingestion
# Body: {"force": true}
```

**Process:**
- Bypasses all checks
- Re-ingests ALL 26 servers regardless of existing data
- Same behavior as before this enhancement

## Skip Reasons

The system tracks why each server was processed or skipped:

| Reason | Description |
|--------|-------------|
| `unchanged` | Content hash matches, no changes detected |
| `content_changed` | Content hash differs, source was updated |
| `index_missing` | Collection doesn't exist in OpenSearch |
| `index_empty` | Collection exists but has no documents |
| `no_collection_mapping` | MTM not found in mapper |
| `no_hash` | Existing documents lack content_hash metadata |
| `forced` | Force re-ingest parameter was true |
| `scraper_error` | Couldn't scrape to check hash |
| `check_error` | Error during skip check |

## API Response

### Start Bulk Ingestion
```json
{
  "success": true,
  "message": "Bulk ingestion started for 26 servers (force=false)",
  "total": 26,
  "force_reingest": false
}
```

### Bulk Ingestion Status
```json
{
  "in_progress": true,
  "current_server": "S924 (9009-42A)",
  "completed": ["9080-HEU", "9043-MRU"],
  "skipped": [
    {"mtm": "9824-42A", "model": "S1124", "reason": "unchanged"},
    {"mtm": "9824-22A", "model": "S1122", "reason": "unchanged"}
  ],
  "failed": [],
  "completed_count": 2,
  "skipped_count": 2,
  "failed_count": 0,
  "total": 26,
  "started_at": "2026-05-27T10:00:00",
  "force_reingest": false
}
```

## Benefits

### Time Savings
- **Before**: ~45-60 minutes to re-ingest all 26 servers
- **After**: ~5-10 minutes if most servers unchanged
- **Typical scenario**: Only 1-3 servers change per week

### Resource Efficiency
- Reduces load on Code Engine scraper
- Minimizes OpenSearch write operations
- Saves embedding generation costs (if using paid API)

### Scraper Health
- Fewer cold starts (scraper stays warm longer)
- More predictable response times
- Better for demo scenarios

## Usage Examples

### Scenario 1: Weekly Maintenance Check
```bash
# Check for any updated Sales Manuals
curl -X POST https://rag-backend-rag-demo.apps.p1265.cecc.ihost.com/api/start-bulk-ingestion \
  -H "Content-Type: application/json"

# Most servers will be skipped, only changed ones re-ingested
```

### Scenario 2: New Deployment / Testing
```bash
# Force re-ingest everything to ensure clean state
curl -X POST https://rag-backend-rag-demo.apps.p1265.cecc.ihost.com/api/start-bulk-ingestion \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

### Scenario 3: Single Server Update
```bash
# If you know S924 manual was updated, use single ingestion endpoint
curl -X POST https://rag-backend-rag-demo.apps.p1265.cecc.ihost.com/api/ingest-sales-manual \
  -H "Content-Type: application/json" \
  -d '{
    "mtm": "9009-42A",
    "server_model": "S924",
    "server_name": "IBM Power System S924",
    "processor": "POWER9",
    "url": "https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42a"
  }'
```

## Monitoring

### Check Status During Ingestion
```bash
curl https://rag-backend-rag-demo.apps.p1265.cecc.ihost.com/api/bulk-ingestion-status
```

### View Logs
```bash
oc logs -f deployment/rag-backend -n rag-demo | grep "Bulk Ingestion"
```

**Key log messages:**
- `⏭️ Skipped` - Server was skipped (unchanged)
- `🔄 content changed` - Server is being re-ingested (source updated)
- `✓ completed` - Server ingestion successful

## Technical Details

### Content Hash Storage
- Stored in OpenSearch document metadata: `content_hash`
- SHA-256 hash of full Sales Manual text
- Also includes: `ingestion_timestamp`, `content_length`, `chunker_version`

### Collection Naming
- Format: `rag_mtm_{mtm}` (e.g., `rag_mtm_9009_42a`)
- Hashed to: `rag_{md5_hash}` for OpenSearch index name
- Consistent with existing MTM-based architecture

### Skip Check Performance
- Lightweight scrape to get content (~10-20 seconds per server)
- Hash calculation is fast (< 1 second)
- OpenSearch query is fast (< 1 second)
- **Total check time: ~15-25 seconds per server**
- **Skip saves: ~2-3 minutes of full ingestion per server**

## Future Enhancements

Potential improvements for consideration:

1. **HEAD request optimization**: Check Last-Modified header before scraping
2. **Batch hash checking**: Check multiple servers in parallel
3. **Scheduled checks**: Automatic daily/weekly change detection
4. **Notification system**: Alert when new content is detected
5. **Partial updates**: Only re-chunk changed sections (advanced)

## Troubleshooting

### All Servers Being Re-ingested
- Check if `force=true` was passed
- Verify content_hash exists in OpenSearch documents
- Check scraper connectivity

### Servers Not Being Skipped When They Should
- Content may have actually changed (check IBM docs site)
- Scraper may be returning different formatting
- Hash calculation may be inconsistent

### False Positives (Skipping Changed Content)
- Very rare - hash comparison is deterministic
- Could indicate scraper caching issue
- Use `force=true` to override

## Related Files

- `app.py` - Main bulk ingestion logic (lines 2203-2420)
- `sales_manual_chunker.py` - Content hash calculation (line 47)
- `server_mtm_mapper.py` - MTM to collection name mapping
- `table_lookup_service.py` - Index name generation (line 17-20)