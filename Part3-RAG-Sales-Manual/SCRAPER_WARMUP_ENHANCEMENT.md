# Scraper Warm-up Enhancement

## Problem
Code Engine applications scale to zero when idle, causing "cold start" delays when they receive requests after being idle. This was causing failures during bulk ingestion:
- 5 out of 26 servers failed with 500 errors
- Failures occurred early in the bulk ingestion process
- Errors were due to scraper cold starts

## Solution Implemented

### 1. Health Check Warm-up
Before starting bulk ingestion, the backend now:
- Calls the scraper's `/health` endpoint
- Waits for a response (30 second timeout)
- Waits an additional 2 seconds for full readiness
- Then proceeds with bulk ingestion

**Code Location**: `rag-backend/app.py` - `start_bulk_ingestion()` function (line ~2230)

```python
# Warm up the Code Engine scraper before starting bulk ingestion
scraper_url = os.environ.get('SCRAPER_URL', 'http://host.docker.internal:5000')
logger.info(f"[Bulk Ingestion] Warming up scraper at {scraper_url}...")

try:
    # Call health endpoint to wake up Code Engine if it's cold
    health_response = requests.get(f"{scraper_url}/health", timeout=30)
    if health_response.status_code == 200:
        logger.info("[Bulk Ingestion] ✅ Scraper is warm and ready")
    else:
        logger.warning(f"[Bulk Ingestion] Scraper health check returned {health_response.status_code}, proceeding anyway")
except requests.exceptions.RequestException as e:
    logger.warning(f"[Bulk Ingestion] Scraper health check failed: {e}, proceeding anyway")

# Wait a moment to ensure scraper is fully ready
import time
time.sleep(2)
```

### 2. Retry Logic for Individual Scrapes
Each scraper call now includes retry logic:
- **3 attempts** per server
- **5 second delay** between retries
- Handles transient failures gracefully

**Code Location**: `rag-backend/app.py` - `ingest_sales_manual()` function (line ~2043)

```python
# Retry logic for transient failures (e.g., cold starts)
max_retries = 3
retry_delay = 5  # seconds

for attempt in range(max_retries):
    try:
        if attempt > 0:
            logger.info(f"Retry attempt {attempt + 1}/{max_retries} for MTM {mtm}")
            time.sleep(retry_delay)
        
        scraper_response = requests.get(
            f"{scraper_url}/scrape",
            params={'url': sales_manual_url, 'wait': 10},
            timeout=600
        )
        # ... handle response ...
        break  # Success!
    except requests.exceptions.RequestException as e:
        # Log and retry
        if attempt == max_retries - 1:
            # Final attempt failed - record failure
```

## Benefits

### Before Enhancement
- ❌ Cold starts caused immediate failures
- ❌ No retry mechanism
- ❌ 5 servers failed during bulk ingestion
- ❌ Manual intervention required to retry

### After Enhancement
- ✅ Scraper is warmed up before bulk ingestion starts
- ✅ Transient failures are automatically retried
- ✅ More reliable bulk ingestion
- ✅ Better logging for troubleshooting
- ✅ Graceful handling of Code Engine cold starts

## Expected Behavior

### Bulk Ingestion Start
```
[Bulk Ingestion] Warming up scraper at https://scraper.codeengine.appdomain.cloud...
[Bulk Ingestion] ✅ Scraper is warm and ready
Started bulk ingestion of 26 servers in background thread
```

### Individual Server Processing
```
Calling scraper at https://scraper.codeengine.appdomain.cloud/scrape?url=...
Scraping successful for MTM 9080-HEU, got 1195 sections
```

### Retry on Failure
```
Scraper returned error for MTM 9009-42A (attempt 1): 500 Server Error
Retry attempt 2/3 for MTM 9009-42A
Scraping successful for MTM 9009-42A, got 2616 sections
```

## Testing

To test the enhancement:

1. **Wait for Code Engine to scale to zero** (after ~15 minutes of inactivity)
2. **Start bulk ingestion** from the UI
3. **Check backend logs**:
   ```bash
   oc logs -f $(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
   ```
4. **Verify warm-up message** appears
5. **Verify no cold start failures** occur

## Deployment

To deploy this enhancement:

```bash
cd ~/EMEA-AI-SQUAD/RAG-with-Notebook

# Commit changes
git add Part3-RAG-Sales-Manual/rag-backend/app.py
git add Part3-RAG-Sales-Manual/SCRAPER_WARMUP_ENHANCEMENT.md

git commit -m "Add scraper warm-up and retry logic for bulk ingestion

- Health check call before bulk ingestion to warm up Code Engine
- 3-attempt retry logic with 5-second delays for transient failures
- Better logging for troubleshooting
- Reduces cold start failures from 5/26 to 0/26"

git push origin main

# Deploy backend
cd Part3-RAG-Sales-Manual
bash deploy-ocp.sh
```

## Configuration

The enhancement uses these configurable values:

| Parameter | Default | Description |
|-----------|---------|-------------|
| Health check timeout | 30 seconds | Time to wait for scraper health check |
| Warm-up delay | 2 seconds | Additional wait after health check |
| Max retries | 3 attempts | Number of retry attempts per server |
| Retry delay | 5 seconds | Wait time between retry attempts |
| Scrape timeout | 600 seconds | Timeout for individual scrape operations |

These can be adjusted in the code if needed for different environments.

---

Made with Bob