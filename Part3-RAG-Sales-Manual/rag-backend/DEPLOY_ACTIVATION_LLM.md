# Deploying the Activation Feature LLM Enhancement

## Overview
This guide explains how to deploy the enhanced activation feature service that uses **Granite 4 LLM** to generate clearer descriptions.

## What Changed
The `activation_feature_service.py` now:
1. **Uses Granite LLM** (not TinyLlama) to generate clear descriptions from messy Sales Manual chunks
2. **Passes full chunk text** to Granite for better context understanding
3. **Adds AI-generated disclaimer** to inform users descriptions may contain inaccuracies
4. Falls back to manual extraction if Granite is unavailable
5. Organizes output by category (Processor/Memory/Other)
6. Removes duplicate feature codes and cleans up formatting

## Prerequisites
- Granite LLM service must be running and accessible
- Backend service must be able to reach the LLM service
- No changes to dependencies required (uses existing `requests` library)

## Deployment Steps

### Option 1: Automatic Deployment (Recommended)
Use the existing deployment script which will pick up the changes:

```powershell
# From Part3-RAG-Sales-Manual/rag-backend directory
.\deploy.ps1
```

Or on Linux/Mac:
```bash
./deploy.sh
```

### Option 2: Manual Deployment

#### Step 1: Verify Changes
```powershell
# Check that the file has been updated
git diff activation_feature_service.py
```

#### Step 2: Build New Container
```powershell
# Build the container with the updated code
oc start-build rag-backend --from-dir=. --follow
```

#### Step 3: Wait for Deployment
```powershell
# Watch the deployment
oc get pods -w
```

#### Step 4: Verify Service
```powershell
# Check logs for LLM integration
oc logs -f deployment/rag-backend | Select-String "LLM"
```

## Configuration

### Environment Variables
The service uses these environment variables (already configured):
- `GRANITE_HOST`: Hostname of Granite LLM service (default: `granite-llama-service`)
- `GRANITE_PORT`: Port of Granite LLM service (default: `8080`)

No changes needed to existing ConfigMaps or Secrets.

## Testing

### 1. Local Testing (Before Deployment)
```powershell
# Set up local environment
$env:GRANITE_HOST = "localhost"
$env:GRANITE_PORT = "8080"

# Run test script
python test_activation_llm.py
```

Or use the PowerShell test script:
```powershell
.\test-activation-llm.ps1
```

### 2. Integration Testing (After Deployment)
Test with activation queries through the UI or API:

```powershell
# Get the backend route
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'

# Test activation query
$body = @{
    question = "What processor activations are available for the E1080?"
    collection_name = "e1080"
    llm_service = "granite"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://$BACKEND_URL/query" -Method POST -Body $body -ContentType "application/json"
```

### 3. Expected Results

#### Before Enhancement
```
- EDAR: (#EDAR) -512 GB Base Memory activation (Pools 2.0) from Static Feature EDAR not orderable in China (#EDAS) -500 GB Base Memory activation...
```

#### After Enhancement
```
Currently Available:

Note: Feature descriptions are AI-generated from sales manual content and may contain inaccuracies.

Memory Activations:
- #EDAR: 512 GB base memory activation for Pools 2.0 systems, not orderable in China
- #EDAS: 500 GB base memory activation for Pools 2.0 systems, not orderable in China

Processor Activations:
- #EDPB: 1 core processor activation for EDP2 systems, compatible with Pools 2.0
```

**Key Improvements:**
- ✅ Uses Granite (not TinyLlama) for enhanced capabilities
- ✅ Passes full chunk for better context
- ✅ Concise one-line descriptions
- ✅ AI-generated disclaimer for transparency

## Monitoring

### Check LLM Integration
```powershell
# View logs for LLM description generation
oc logs -f deployment/rag-backend | Select-String "Generated LLM description"
```

### Check Fallback Usage
```powershell
# View logs for fallback to manual extraction
oc logs -f deployment/rag-backend | Select-String "Failed to generate LLM description"
```

## Troubleshooting

### Issue: LLM Descriptions Not Generated
**Symptoms**: Logs show "Failed to generate LLM description" or "LLM request failed"

**Solutions**:
1. Verify Granite service is running:
   ```powershell
   oc get pods | Select-String "granite"
   ```

2. Check Granite service endpoint:
   ```powershell
   oc get svc granite-llama-service
   ```

3. Test Granite connectivity from backend pod:
   ```powershell
   $POD = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}'
   oc exec $POD -- curl -s http://granite-llama-service:8080/health
   ```

### Issue: Descriptions Still Messy
**Symptoms**: Descriptions contain duplicate feature codes or unclear text

**Solutions**:
1. Check if LLM is actually being used:
   ```powershell
   oc logs deployment/rag-backend | Select-String "Generated LLM description"
   ```

2. If no LLM logs, verify the service is initialized with LLM enabled:
   ```python
   # In app.py, the service should be created as:
   activation_service = ActivationFeatureService()  # LLM enabled by default
   ```

3. Adjust LLM prompt temperature (in activation_feature_service.py):
   ```python
   "temperature": 0.3,  # Lower = more focused, Higher = more creative
   ```

### Issue: Slow Response Times
**Symptoms**: Activation queries take longer than expected

**Solutions**:
1. Check LLM response time:
   ```powershell
   oc logs deployment/rag-backend | Select-String "LLM"
   ```

2. Reduce timeout if needed (in activation_feature_service.py):
   ```python
   timeout=10  # Reduce to 5 if needed
   ```

3. Consider disabling LLM for specific queries:
   ```python
   service = ActivationFeatureService(use_llm_descriptions=False)
   ```

## Rollback

If issues occur, rollback to previous version:

```powershell
# Rollback deployment
oc rollout undo deployment/rag-backend

# Verify rollback
oc rollout status deployment/rag-backend
```

## Performance Impact

### Expected Changes
- **Response Time**: +1-2 seconds per activation query (LLM processing)
- **Quality**: Significantly improved description clarity
- **Reliability**: Fallback ensures no failures

### Optimization Tips
1. **Cache descriptions**: Consider storing LLM-generated descriptions in OpenSearch metadata
2. **Batch processing**: Process multiple features in one LLM call (future enhancement)
3. **Async processing**: Generate descriptions asynchronously (future enhancement)

## Next Steps

After successful deployment:
1. Monitor logs for LLM usage patterns
2. Collect user feedback on description quality
3. Consider fine-tuning the LLM prompt based on results
4. Explore caching strategies for frequently accessed features

## Support

For issues or questions:
1. Check logs: `oc logs -f deployment/rag-backend`
2. Review documentation: `ACTIVATION_LLM_ENHANCEMENT.md`
3. Test locally: `python test_activation_llm.py`