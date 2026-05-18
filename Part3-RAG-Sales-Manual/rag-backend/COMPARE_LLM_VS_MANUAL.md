# Compare LLM vs Manual Extraction

Based on your logs, here's what we're seeing:

## Feature: EDAR

### Granite LLM Output (11.22 seconds)
```
EDAR is for activating 512 GB of base memory using Pools 2.0 from Static, not orderable in China
```

### Manual Extraction (instant)
We need to see what the manual extraction produces for EDAR. The Sales Manual likely has:
```
(#EDAR) 512 GB Base Memory activation (Pools 2.0) from Static
```

So manual extraction should produce:
```
512 GB Base Memory activation (Pools 2.0) from Static
```

## Analysis

**Granite LLM:**
- ✅ Adds "is for activating" (more natural language)
- ✅ Includes "not orderable in China" restriction
- ❌ Takes 11+ seconds
- ❌ Causes timeout when combined with other processing

**Manual Extraction:**
- ✅ Fast (< 0.1 seconds)
- ✅ Matches Sales Manual format exactly
- ✅ Clean, concise
- ❌ Doesn't add natural language phrasing
- ❌ May miss restrictions in "Note:" sections

## What We Need to See

To make an informed decision, we need to compare the actual output. Can you:

1. **Check the UI response** - What did features 2-10 look like (manual extraction)?
2. **Compare with feature 1** - Was the Granite description significantly better?

## Quick Test

Run this to see both outputs side-by-side:

```powershell
# Get backend URL
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'

# Query activations
$body = @{
    question = "What activations are available?"
    collection_name = "rag_36d5fcdd8f17c37ef0f739637cde0718"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://$BACKEND_URL/api/search" -Method Post -Body $body -ContentType "application/json" -SkipCertificateCheck -TimeoutSec 60

# Show features
$response.features | ForEach-Object {
    Write-Host "Feature: #$($_.feature_code)" -ForegroundColor Yellow
    Write-Host "Description: $($_.description)" -ForegroundColor White
    Write-Host ""
}
```

## Decision Matrix

| Aspect | Granite LLM | Manual Extraction |
|--------|-------------|-------------------|
| Speed | 11+ seconds | < 0.1 seconds |
| Quality | Natural language | Sales Manual format |
| Restrictions | Includes notes | May miss notes |
| Timeout Risk | High | None |
| Consistency | Variable | Consistent |

## Options

### Option 1: Keep LLM, Fix Timeout
- Reduce Granite timeout from 30s to 5s
- Accept that some features won't get LLM descriptions
- Still risk of timeout

### Option 2: Disable LLM Entirely
- Fast, reliable
- Lose natural language phrasing
- Lose restriction notes

### Option 3: Hybrid with Better Timeout
- Set `max_llm_calls=0` (disable)
- Add LLM enhancement as future feature
- Focus on making manual extraction perfect

## Recommendation

**First, let's see the actual output quality.** If the manual extraction looks good enough, we should disable LLM to avoid timeouts. If Granite adds significant value, we need to fix the timeout issue differently (async processing, caching, etc.).

Can you share what the UI showed for features 2-10 (manual extraction)?