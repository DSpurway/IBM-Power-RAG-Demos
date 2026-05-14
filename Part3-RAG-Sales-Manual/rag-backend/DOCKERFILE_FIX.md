# Dockerfile Fix - Missing activation_feature_service.py

## Problem
The backend was crashing on startup with:
```
ModuleNotFoundError: No module named 'activation_feature_service'
```

## Root Cause
The `activation_feature_service.py` file was not included in the Dockerfile COPY commands, even though:
1. The file exists in the repository
2. It's imported by `app.py` (line 33)
3. It's used for activation feature queries

## Solution
Added `activation_feature_service.py` to both stages of the Dockerfile:

**Builder stage (line 55):**
```dockerfile
COPY activation_feature_service.py .
```

**Production stage (line 91):**
```dockerfile
COPY --from=builder /app/activation_feature_service.py .
```

## Impact
This was the PRIMARY issue breaking server lifecycle questions. The backend couldn't start at all, so no queries were working.

## Secondary Issue (Already Fixed)
The `query_classifier.py` also had a secondary issue where regex-based entity extraction was removed as a fallback when Watson Assistant is unavailable. This has been fixed to restore regex fallback.

## Deployment
To deploy the fix:
```powershell
cd Part3-RAG-Sales-Manual/rag-backend
.\deploy.ps1
```

Wait for the pod to restart and check logs:
```powershell
oc logs -f deployment/rag-backend --tail=50
```

You should see:
- "Web scraping module loaded successfully"
- "OpenSearch client initialized successfully"
- No crash errors

## Testing
After deployment, test with a lifecycle query:
```powershell
cd Part3-RAG-Sales-Manual
.\test-lifecycle-query.ps1
```

Expected: Successful response with lifecycle dates from the sales manual.