# Activation Feature LLM Timeout Diagnostic

## Problem Summary
The backend is experiencing timeouts when calling the Granite service to generate concise descriptions for activation features:
```
WARNING:activation_feature_service:Failed to generate Granite description for EMAC: 
HTTPConnectionPool(host='granite-service', port=8080): Read timed out. (read timeout=15)
```

## Changes Made for Diagnosis

### 1. Increased Timeout (activation_feature_service.py)
- **Changed from**: `timeout=10` seconds
- **Changed to**: `timeout=30` seconds
- **Reason**: To determine if Granite can complete the request given more time

### 2. Added Timing Logs (activation_feature_service.py)
- Added `start_time` and `elapsed_time` tracking
- Logs now show: `"Granite LLM response received in X.XX seconds"`
- This will help us understand actual response times

### 3. Better Error Handling (activation_feature_service.py)
- Separate handling for `requests.exceptions.Timeout` vs other exceptions
- More informative error messages

### 4. Kept Rate Limiting (app.py & activation_feature_service.py)
- Still limiting to `max_llm_calls=3` to prevent excessive timeouts
- LLM descriptions are still enabled (`use_llm_descriptions=True`)

## What to Look For in Logs

After deploying these changes, check the backend logs for:

### Success Case:
```
INFO:activation_feature_service:Requesting Granite LLM description for EMAC (call 1/3)
INFO:activation_feature_service:Granite LLM response received in 12.34 seconds
INFO:activation_feature_service:Generated Granite description for EMAC: ...
```

### Timeout Case:
```
INFO:activation_feature_service:Requesting Granite LLM description for EMAC (call 1/3)
WARNING:activation_feature_service:Granite LLM timeout for EMAC - skipping (Granite service may be overloaded)
```

### Partial Success:
```
INFO:activation_feature_service:Requesting Granite LLM description for EMAC (call 1/3)
INFO:activation_feature_service:Granite LLM response received in 8.45 seconds
INFO:activation_feature_service:Requesting Granite LLM description for EDP4 (call 2/3)
WARNING:activation_feature_service:Granite LLM timeout for EDP4 - skipping
INFO:activation_feature_service:Requesting Granite LLM description for EDP2 (call 3/3)
INFO:activation_feature_service:Granite LLM response received in 25.67 seconds
INFO:activation_feature_service:Extraction complete: 10 features found, 3 LLM calls made
```

## Testing Steps

1. **Deploy the updated backend**:
   ```powershell
   cd Part3-RAG-Sales-Manual/rag-backend
   ./deploy.ps1
   ```

2. **Query for activation features**:
   - Ask: "What activation features are available for the E1080?"
   - Or: "Can I still buy processor activations for S922?"

3. **Check the backend logs**:
   ```powershell
   oc logs -f deployment/rag-backend-service
   ```

4. **Analyze the timing data**:
   - If responses come back in < 15 seconds: Granite is working, original timeout was too short
   - If responses timeout at 30 seconds: Granite is too slow or overloaded
   - If some succeed and some fail: Granite performance is inconsistent

## Possible Outcomes & Next Steps

### Outcome 1: All LLM Calls Succeed (< 30s each)
- **Conclusion**: Original 10s timeout was too aggressive
- **Action**: Keep 30s timeout, or reduce to 20s for safety
- **Result**: Users get AI-generated descriptions ✅

### Outcome 2: All LLM Calls Timeout (> 30s)
- **Conclusion**: Granite service is overloaded or model is too slow
- **Action**: Disable LLM descriptions (`use_llm_descriptions=False`)
- **Result**: Users get manual extraction (still accurate, just less polished)

### Outcome 3: Mixed Results (some succeed, some timeout)
- **Conclusion**: Granite performance is inconsistent
- **Action**: Reduce `max_llm_calls` to 1 or 2, or disable entirely
- **Result**: Only first 1-2 features get AI descriptions

### Outcome 4: Timeouts Still at 15 Seconds
- **Conclusion**: There's a gateway or proxy timeout we can't control
- **Action**: Disable LLM descriptions or reduce `max_llm_calls` to 1
- **Result**: Minimize timeout impact on user experience

## Configuration Options

You can adjust these parameters in `app.py`:

```python
# Option 1: Enable with limited calls (current setting)
activation_service = ActivationFeatureService(use_llm_descriptions=True, max_llm_calls=3)

# Option 2: Enable with fewer calls (safer)
activation_service = ActivationFeatureService(use_llm_descriptions=True, max_llm_calls=1)

# Option 3: Disable LLM descriptions (fastest, most reliable)
activation_service = ActivationFeatureService(use_llm_descriptions=False)
```

## Performance Expectations

### With LLM Descriptions (current):
- **Best case**: 3 calls × 10s = 30 seconds
- **Worst case**: 3 calls × 30s = 90 seconds (may hit gateway timeout)
- **Quality**: AI-generated, concise descriptions

### Without LLM Descriptions:
- **Time**: < 1 second (instant)
- **Quality**: Manual extraction from sales manual (still accurate)

## Recommendation

Based on the logs, if you see consistent timeouts even at 30 seconds, I recommend:

1. **Short term**: Disable LLM descriptions for reliability
2. **Long term**: Investigate Granite service performance or consider:
   - Using a faster model
   - Caching LLM-generated descriptions
   - Pre-generating descriptions during ingestion
   - Using async/parallel LLM calls

---
*Diagnostic changes made: 2026-05-15*
*Purpose: Determine if Granite service can complete requests with more time*