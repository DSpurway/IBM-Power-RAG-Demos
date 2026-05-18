# Activation Feature Timeout Fix

## Problem
504 timeout on UI when querying activations. Logs show:
- Granite LLM call takes 11+ seconds for first feature
- Total processing time exceeds UI timeout
- Manual extraction works fine for features 2-10

## Root Cause
Even with `max_llm_calls=1`, that single Granite call is too slow and causes timeout.

## Solution
**Disable LLM calls entirely** - the improved manual extraction is good enough.

## Change Made

**File:** `Part3-RAG-Sales-Manual/rag-backend/app.py` (line 850)

**Before:**
```python
activation_service = ActivationFeatureService(max_llm_calls=1)
```

**After:**
```python
activation_service = ActivationFeatureService(use_llm_descriptions=False)
```

## Deploy the Fix

```powershell
cd Part3-RAG-Sales-Manual\rag-backend

# Build and deploy
oc start-build rag-backend --from-dir=. --follow
oc rollout restart deployment/rag-backend
oc rollout status deployment/rag-backend
```

## Expected Result

**Before (with LLM):**
- Processing time: 11+ seconds
- Result: 504 timeout
- Only first feature gets LLM description

**After (manual only):**
- Processing time: < 2 seconds
- Result: Success
- All features get clean manual descriptions

## Verification

Check logs - should see:
```
INFO:activation_feature_service:Processing 20 chunks for activation features (max 0 LLM calls)
INFO:activation_feature_service:Extraction complete: 10 features found, 0 LLM calls made
```

No more "Requesting Granite LLM description" messages.

## Why This Works

The improved manual extraction now produces clean descriptions:
- Extracts just the title line from Sales Manual
- Removes feature code prefix
- No artifacts or duplicates
- Fast and reliable

Example output:
```
#EDAR: 512 GB Base Memory activation (Pools 2.0) from Static
#EMAC: 512 GB Memory Activation for #EHC9 no cost
#EDP2: 1 core Processor Activation for EDP2
```

## If You Want LLM Enhancement Later

Consider these options:
1. **Async processing** - Return manual extraction immediately, enhance with LLM in background
2. **Caching** - Cache LLM results in OpenSearch metadata
3. **Faster model** - Use a smaller/faster model than Granite
4. **Reduced timeout** - Lower Granite timeout from 30s to 5s

But for now, manual extraction is sufficient and fast.