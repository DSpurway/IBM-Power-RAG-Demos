# Activation Feature LLM Timeout Fix

## Problem
Gateway timeout errors were occurring when querying activation features because the system was making sequential LLM calls to the Granite service for each activation feature found. With many features (10-20+), this could take 150-300 seconds total, exceeding typical gateway timeout limits.

## Root Cause
The `ActivationFeatureService` was calling the Granite LLM service for **every** activation feature to generate cleaner descriptions. Each call had a 15-second timeout, and they were processed sequentially:
- 10 features × 15 seconds = 150 seconds
- 20 features × 15 seconds = 300 seconds

This exceeded typical gateway timeout limits (usually 60-120 seconds).

## User Feedback
The initial fix used `max_llm_calls=10`, but we don't actually know if 10 works without testing. A more conservative approach is better to ensure reliability.

## Solution
Implemented a **conservative rate limiting mechanism** with the following improvements:

### 1. Maximum LLM Calls Limit
- Added `max_llm_calls` parameter (default: 3) to limit the number of LLM description requests
- After reaching the limit, remaining features fall back to manual text extraction
- Conservative limit of 3 ensures reliability: 3 calls × 10 seconds = ~30 seconds max
- This is well within typical gateway timeout limits (60-120 seconds)

### 2. Reduced Individual Timeout
- Reduced individual LLM call timeout from 15 seconds to 10 seconds
- This provides faster failure recovery and reduces overall processing time

### 3. Call Tracking and Logging
- Added `llm_calls_made` counter to track how many LLM calls have been made
- Enhanced logging to show progress: "call X/Y" for each LLM request
- Logs summary at the end: "X features found, Y LLM calls made"

### 4. User Notification
- Updated the AI disclaimer to inform users when partial LLM descriptions are used
- Shows: "AI-generated descriptions shown for first 3 feature(s) to prevent timeouts"

## Code Changes

### activation_feature_service.py
1. **Constructor** - Added `max_llm_calls` parameter and counter initialization
2. **_generate_llm_description()** - Added call limit check and reduced timeout
3. **extract_features_from_chunks()** - Reset counter and added progress logging
4. **generate_activation_answer()** - Enhanced disclaimer for partial LLM usage

### app.py
- Updated both instances of `ActivationFeatureService()` to pass `max_llm_calls=3`
- Added explanatory comments about timeout prevention

## Performance Impact

### Before Fix
- **Worst case**: 20 features × 15s = 300 seconds → Gateway timeout ❌
- **Best case**: 5 features × 15s = 75 seconds → Slow but works

### After Fix (Conservative Approach)
- **Worst case**: 3 LLM calls × 10s + 17 manual extractions = ~30 seconds → Fast and reliable ✅
- **Best case**: 3 features × 10s = 30 seconds → Consistent performance
- **Guaranteed**: Never exceeds ~30 seconds for LLM processing
- **Trade-off**: Only first 3 features get AI descriptions, but all features are still shown with manual extraction

## Configuration Options

The `max_llm_calls` parameter can be adjusted based on your needs:

```python
# More LLM descriptions (slower, better quality)
activation_service = ActivationFeatureService(max_llm_calls=15)

# Fewer LLM descriptions (faster, mixed quality)
activation_service = ActivationFeatureService(max_llm_calls=5)

# No LLM descriptions (fastest, manual extraction only)
activation_service = ActivationFeatureService(use_llm_descriptions=False)
```

## Testing Recommendations

1. **Test with many features**: Query a server with 15+ activation features
2. **Monitor timing**: Check backend logs for "X features found, Y LLM calls made"
3. **Verify quality**: Ensure first 3 features have good AI-generated descriptions
4. **Check fallback**: Verify features 4+ still have readable descriptions from manual extraction
5. **Adjust if needed**: If 3 is too conservative and no timeouts occur, increase `max_llm_calls` to 5 or 7

## Future Enhancements

Potential improvements for better performance:

1. **Async/Parallel Processing**: Use asyncio to make multiple LLM calls in parallel
2. **Caching**: Cache LLM-generated descriptions by feature code
3. **Batch Processing**: Send multiple features to LLM in a single request
4. **Progressive Loading**: Return partial results to UI as they become available

## Deployment

To deploy this fix:

```powershell
# From the rag-backend directory
cd Part3-RAG-Sales-Manual/rag-backend
./deploy.ps1
```

Or use the cleanup and redeploy script:
```powershell
./cleanup-and-redeploy.ps1
```

## Related Files
- `activation_feature_service.py` - Main service with LLM integration
- `app.py` - Backend API that uses the service
- `ACTIVATION_LLM_ENHANCEMENT.md` - Original LLM enhancement documentation

---
*Fix implemented: 2026-05-15*
*Issue: Gateway timeout on activation feature queries*
*Solution: Rate limiting with max_llm_calls parameter*