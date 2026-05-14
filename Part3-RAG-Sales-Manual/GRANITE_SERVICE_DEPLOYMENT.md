# Granite Service Deployment Summary

## Overview

The Granite service has been successfully created for the Hybrid Cloud RAG demo. This service provides a more advanced language model (Granite 4.0 Micro) for handling complex technical questions that require better reasoning capabilities than TinyLlama.

## What Was Created

### 1. Granite Service Directory Structure
```
Part3-RAG-Sales-Manual/granite-service/
├── Dockerfile                  # Container image with Granite 4.0 Micro model
├── granite-deploy.yaml         # Kubernetes deployment configuration
├── granite-svc.yaml           # Kubernetes service configuration
├── granite-route.yaml         # OpenShift route for external access
├── deploy.sh                  # Bash deployment script
├── deploy.ps1                 # PowerShell deployment script
└── README.md                  # Comprehensive documentation
```

### 2. Model Information
- **Model**: IBM Granite 4.0 Micro (Q4_K_M quantization)
- **Size**: ~2.5 GB
- **Parameters**: ~4 billion
- **Context Window**: 4096 tokens
- **Source**: [HuggingFace](https://huggingface.co/ibm-granite/granite-4.0-micro-GGUF)

### 3. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    RAG Backend                          │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Query Classifier                         │  │
│  │  (Determines query complexity)                   │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │                                     │
│         ┌─────────▼──────────┐                         │
│         │  Simple Query?     │                         │
│         │  (Lifecycle, etc)  │                         │
│         └─────────┬──────────┘                         │
│                   │                                     │
│          ┌────────▼────────┐                           │
│          │   TinyLlama     │                           │
│          │   Service       │                           │
│          │   (Part 1 & 2)  │                           │
│          └─────────────────┘                           │
│                                                         │
│         ┌─────────────────────┐                        │
│         │  Complex Query?     │                        │
│         │  (Technical, Sales) │                        │
│         └─────────┬───────────┘                        │
│                   │                                     │
│          ┌────────▼────────┐                           │
│          │   Granite       │                           │
│          │   Service       │                           │
│          │   (Part 3)      │◄─── NEW SERVICE          │
│          └─────────────────┘                           │
└─────────────────────────────────────────────────────────┘
```

## Deployment Instructions

### Quick Deploy

**Linux/Mac:**
```bash
cd Part3-RAG-Sales-Manual/granite-service
chmod +x deploy.sh
./deploy.sh
```

**Windows (PowerShell):**
```powershell
cd Part3-RAG-Sales-Manual\granite-service
.\deploy.ps1
```

### Manual Deployment

```bash
# 1. Navigate to the granite-service directory
cd Part3-RAG-Sales-Manual/granite-service

# 2. Build the container image
oc new-build --name=granite-service --binary --strategy=docker
oc start-build granite-service --from-dir=. --follow

# 3. Deploy the service
oc apply -f granite-deploy.yaml
oc apply -f granite-svc.yaml
oc apply -f granite-route.yaml

# 4. Wait for deployment to be ready
oc rollout status deployment/granite-service --timeout=10m
```

### Verification

```bash
# Check pod status
oc get pods -l app=granite-service

# Test health endpoint
GRANITE_URL=$(oc get route granite-service -o jsonpath='{.spec.host}')
curl https://$GRANITE_URL/health

# Expected response: {"status":"ok"}
```

## Integration with RAG Backend

### Environment Variables

The RAG backend has been updated to support both services:

```yaml
env:
  # Granite Service (for complex RAG queries - Part 3)
  - name: GRANITE_HOST
    value: "granite-service"
  - name: GRANITE_PORT
    value: "8080"
  
  # TinyLlama Service (for simple queries - Part 1 & 2)
  - name: TINYLLAMA_HOST
    value: "llama-service"
  - name: TINYLLAMA_PORT
    value: "8080"
  
  # Legacy support - defaults to Granite
  - name: LLAMA_HOST
    value: "granite-service"
  - name: LLAMA_PORT
    value: "8080"
```

### Backend Configuration

The backend (`app.py`) automatically routes queries:
- **TinyLlama**: Simple lifecycle queries, basic demonstrations
- **Granite**: Complex technical questions, sales queries, multi-step reasoning

Configuration in `app.py` (lines 65-76):
```python
# Granite service (for RAG - Part 3)
GRANITE_HOST = os.environ.get('GRANITE_HOST', os.environ.get('LLAMA_HOST', 'granite-llama-service'))
GRANITE_PORT = os.environ.get('GRANITE_PORT', os.environ.get('LLAMA_PORT', '8080'))

# TinyLlama service (for Part 1 - demonstrates hallucinations)
TINYLLAMA_HOST = os.environ.get('TINYLLAMA_HOST', 'tinyllama-service')
TINYLLAMA_PORT = os.environ.get('TINYLLAMA_PORT', '8080')

# Legacy support - default to Granite
LLAMA_HOST = GRANITE_HOST
LLAMA_PORT = GRANITE_PORT
```

## Resource Requirements

### Deployment Configuration

**Requests:**
- Memory: 6 GB
- CPU: 2 cores

**Limits:**
- Memory: 12 GB
- CPU: 4 cores

**Node Requirements:**
- Power10 nodes with MMA support
- Node selector: `feature.node.kubernetes.io/cpu-cpuid.MMA: "true"`

### Adjust Resources

If needed, modify `granite-deploy.yaml`:
```yaml
resources:
  requests:
    memory: "6Gi"
    cpu: "2"
  limits:
    memory: "12Gi"
    cpu: "4"
```

## Updated Deployment Process

The `setup-part3.sh` script has been enhanced to:
1. Check if Granite service is deployed
2. Offer to deploy it automatically if missing
3. Configure the RAG backend to use both services

### Using the Enhanced Setup Script

```bash
cd Part3-RAG-Sales-Manual
./setup-part3.sh
```

The script will:
- Configure CORS for all services
- Check for Granite service
- Prompt to deploy if not found
- Configure backend environment variables

## Comparison: TinyLlama vs Granite

| Feature | TinyLlama | Granite 4.0 Micro |
|---------|-----------|-------------------|
| **Parameters** | 1.1B | 4B |
| **Model Size** | ~1.2 GB | ~2.5 GB |
| **Memory Required** | 2-4 GB | 6-12 GB |
| **Use Case** | Simple demos, lifecycle queries | Complex RAG, technical questions |
| **Accuracy** | Basic, may hallucinate | High accuracy, better reasoning |
| **Speed** | Fast | Moderate |
| **Context Window** | 2048 tokens | 4096 tokens |
| **Best For** | Part 1 & 2 demonstrations | Part 3 advanced queries |

## Testing the Granite Service

### 1. Health Check
```bash
GRANITE_URL=$(oc get route granite-service -o jsonpath='{.spec.host}')
curl https://$GRANITE_URL/health
```

### 2. Simple Completion Test
```bash
curl -X POST https://$GRANITE_URL/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the key features of IBM Power10 processors?",
    "n_predict": 100
  }'
```

### 3. Test Through RAG Backend
```bash
# The backend will automatically route complex queries to Granite
RAG_BACKEND_URL=$(oc get route rag-backend -o jsonpath='{.spec.host}')

curl -X POST https://$RAG_BACKEND_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the advanced RAS features in Power10 systems?",
    "collection": "power-systems"
  }'
```

## Troubleshooting

### Pod Not Starting

**Check logs:**
```bash
oc logs -f deployment/granite-service
```

**Common issues:**
- Insufficient memory → Increase resource limits
- Node selector not matching → Verify Power10 nodes with MMA
- Model download failed → Check network connectivity

### Service Not Responding

**Check endpoints:**
```bash
oc get endpoints granite-service
```

**Verify pod is ready:**
```bash
oc get pods -l app=granite-service
```

### Performance Issues

**Check resource usage:**
```bash
oc adm top pods -l app=granite-service
```

**Optimization options:**
1. Increase CPU/memory limits
2. Adjust thread count in Dockerfile (line 61)
3. Consider smaller quantization (Q3_K_M) for faster inference

## Files Modified

### 1. RAG Backend Deployment
**File**: `Part3-RAG-Sales-Manual/rag-backend/rag-backend-deploy.yaml`
- Added GRANITE_HOST and GRANITE_PORT environment variables
- Added TINYLLAMA_HOST and TINYLLAMA_PORT for explicit service routing
- Updated LLAMA_HOST to default to granite-service

### 2. Setup Script
**File**: `Part3-RAG-Sales-Manual/setup-part3.sh`
- Added Granite service deployment check
- Prompts user to deploy if missing
- Provides status of both LLM services

### 3. Deployment Guide
**File**: `Part3-RAG-Sales-Manual/DEPLOYMENT_GUIDE.md`
- Added LLM Services section
- Documented Granite service deployment steps
- Included verification instructions

## Next Steps

1. **Deploy the Granite Service**
   ```bash
   cd Part3-RAG-Sales-Manual/granite-service
   ./deploy.sh  # or deploy.ps1 on Windows
   ```

2. **Verify Deployment**
   ```bash
   oc get pods -l app=granite-service
   oc logs -f deployment/granite-service
   ```

3. **Update RAG Backend** (if already deployed)
   ```bash
   oc set env deployment/rag-backend \
     GRANITE_HOST=granite-service \
     GRANITE_PORT=8080
   ```

4. **Test Complex Queries**
   - Use the RAG UI to ask technical questions
   - Monitor which service handles each query
   - Compare response quality between TinyLlama and Granite

## Benefits

✅ **Better Accuracy**: Granite provides more accurate responses for complex queries  
✅ **Dual Model Support**: Keep TinyLlama for simple demos, use Granite for advanced features  
✅ **Automatic Routing**: Backend intelligently routes queries to the appropriate model  
✅ **Easy Deployment**: Simple scripts for quick setup  
✅ **Flexible Configuration**: Environment variables for easy customization  
✅ **Production Ready**: Proper health checks, resource limits, and monitoring  

## Related Documentation

- [Granite Service README](granite-service/README.md) - Detailed service documentation
- [Part3 Deployment Guide](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [RAG Backend README](rag-backend/README.md) - Backend configuration details
- [Query Classifier](rag-backend/query_classifier.py) - Query routing logic

---

**Created**: 2026-05-14  
**Status**: Ready for deployment  
**Tested**: Pending user verification