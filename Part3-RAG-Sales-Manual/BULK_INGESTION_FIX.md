# Bulk Ingestion Status Polling Fix

## Problem
When pressing "Load All Documents" button in the UI, the bulk ingestion starts but status updates are not displayed properly. The UI appears to hang without showing progress.

## Root Cause
The polling mechanism had several issues:
1. **Initial delay too short**: 5 seconds wasn't enough for the backend thread to initialize
2. **No error recovery**: If a status poll failed, polling would stop completely
3. **Insufficient logging**: Hard to debug what was happening
4. **No console feedback**: Status updates weren't logged to browser console

## Changes Made

### Frontend (carbon-rag-ui/src/app/sales-manual/page.js)

1. **Reduced initial polling delay** (line 203):
   - Changed from 5 seconds to 2 seconds
   - Backend thread starts quickly, so we can poll sooner

2. **Added error recovery** (lines 147-189):
   - Continue polling even if a status request fails
   - Check `bulkIngestionInProgress` flag before continuing
   - Added console logging for debugging

3. **Enhanced logging**:
   - Added `console.log('[Bulk Ingestion] Status update:', status)` to track updates
   - Added `console.log('[Bulk Ingestion] Started:', data)` when starting
   - Added `console.error('[Bulk Ingestion] Error starting:', err)` for errors

4. **Better error messages**:
   - More descriptive error handling in `handleLoadAllDocuments`
   - Added "Status updates will appear below" to user message

### Backend (rag-backend/app.py)

1. **Enhanced status endpoint logging** (line 1174):
   - Added detailed logging: `in_progress`, `current_server`, `completed_count/total`
   - Helps track backend state during ingestion

## How It Works Now

1. User clicks "Load All Documents"
2. Frontend calls `/api/rag/ingest-all-sales-manuals`
3. Backend starts background thread and returns immediately
4. Frontend waits 2 seconds, then starts polling `/api/rag/bulk-ingestion-status`
5. Backend returns current state (in_progress, current_server, completed, failed)
6. Frontend displays progress bar and status
7. Polling continues every 10 seconds until `in_progress` becomes `false`
8. If any poll fails, it continues polling (doesn't stop)

## Testing

### Check Backend Logs
```bash
# On OCP, check the rag-backend pod logs
oc logs -f deployment/rag-backend

# Look for these log messages:
# [Bulk Ingestion Status] in_progress=True, current=E1180 (9080-HEU), completed=0/26
# [Bulk Ingestion] Processing MTM 9080-HEU - E1180
# [Bulk Ingestion] ✓ E1180 completed
```

### Check Browser Console
Open browser DevTools (F12) and look for:
```
[Bulk Ingestion] Started: {success: true, message: "...", total: 26}
[Bulk Ingestion] Status update: {in_progress: true, current_server: "E1180 (9080-HEU)", ...}
```

### Expected UI Behavior
1. Click "Load All Documents"
2. See message: "Bulk ingestion started! Processing 26 servers. Status updates will appear below."
3. Within 2-3 seconds, see progress tile appear with:
   - Current Server: E1180 (9080-HEU)
   - Progress: 0 of 26 completed
   - Progress bar showing 0%
4. Every 10 seconds, progress updates
5. Completed servers list grows
6. When done, see completion message

## Troubleshooting

### No Status Updates Appearing

**Check 1: Backend is running**
```bash
oc get pods | grep rag-backend
# Should show Running status
```

**Check 2: Backend endpoints are accessible**
```bash
# From within the UI pod or locally with port-forward
curl http://rag-backend:8080/api/bulk-ingestion-status
# Should return JSON with in_progress, current_server, etc.
```

**Check 3: Browser console for errors**
- Open DevTools (F12) → Console tab
- Look for red error messages
- Check Network tab for failed requests

**Check 4: Backend logs**
```bash
oc logs -f deployment/rag-backend | grep "Bulk Ingestion"
```

### Status Shows "Starting..." Forever

This means the backend thread hasn't updated `current_server` yet. Possible causes:
1. Scraper service not accessible
2. Backend thread crashed
3. Network issues between backend and scraper

Check backend logs for errors.

### Polling Stops After First Update

This was the original bug - now fixed. If it still happens:
1. Check browser console for JavaScript errors
2. Verify the fix was deployed (check page.js source in DevTools)
3. Hard refresh browser (Ctrl+Shift+R)

## Deployment

### Rebuild and Deploy UI
```bash
cd Part3-RAG-Sales-Manual/carbon-rag-ui

# Build new image
docker build -t your-registry/carbon-rag-ui:latest .

# Push to registry
docker push your-registry/carbon-rag-ui:latest

# On OCP, restart deployment to pull new image
oc rollout restart deployment/carbon-rag-ui
oc rollout status deployment/carbon-rag-ui
```

### Rebuild and Deploy Backend (if needed)
```bash
cd Part3-RAG-Sales-Manual/rag-backend

# Build new image
docker build -t your-registry/rag-backend:latest .

# Push to registry
docker push your-registry/rag-backend:latest

# On OCP, restart deployment
oc rollout restart deployment/rag-backend
oc rollout status deployment/rag-backend
```

## Verification Script

See `test-bulk-ingestion-status.sh` for automated testing.

---
Made with Bob