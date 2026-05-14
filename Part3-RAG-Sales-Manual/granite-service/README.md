# Granite Service for Complex RAG Queries

This directory contains the deployment files for the Granite 4.0 Micro model service, which is used for handling complex questions in the Hybrid Cloud RAG demo.

## Overview

The Granite service provides a more advanced language model compared to TinyLlama, specifically designed for:
- Complex technical questions
- Multi-step reasoning
- Better understanding of IBM Power Systems documentation
- More accurate responses for sales and technical queries

## Architecture

```
┌─────────────────────┐
│   RAG Backend       │
│                     │
│  ┌──────────────┐   │
│  │Query         │   │
│  │Classifier    │   │
│  └──────┬───────┘   │
│         │           │
│    ┌────▼────┐      │
│    │ Simple? │      │
│    └────┬────┘      │
│         │           │
│    ┌────▼────────┐  │
│    │  Complex?   │  │
│    └────┬────────┘  │
└─────────┼───────────┘
          │
    ┌─────▼──────┐
    │  Granite   │
    │  Service   │
    │  (Port     │
    │   8080)    │
    └────────────┘
```

## Files

- **Dockerfile**: Builds the Granite service container with the Granite 4.0 Micro model
- **granite-deploy.yaml**: Kubernetes deployment configuration
- **granite-svc.yaml**: Kubernetes service configuration
- **granite-route.yaml**: OpenShift route for external access
- **deploy.sh**: Bash deployment script
- **deploy.ps1**: PowerShell deployment script

## Deployment

### Prerequisites

1. OpenShift cluster with Power10 nodes (MMA support)
2. `oc` CLI tool installed and logged in
3. Sufficient resources:
   - 6-12 GB RAM
   - 2-4 CPU cores
   - ~3 GB storage for the model

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
# 1. Build the container image
oc new-build --name=granite-service --binary --strategy=docker
oc start-build granite-service --from-dir=. --follow

# 2. Deploy the service
oc apply -f granite-deploy.yaml
oc apply -f granite-svc.yaml
oc apply -f granite-route.yaml

# 3. Wait for deployment
oc rollout status deployment/granite-service
```

## Configuration

### Environment Variables

The Granite service uses the following configuration:

- **Port**: 8080 (default llama-server port)
- **Context Window**: 4096 tokens
- **Threads**: 16 (optimized for Power10)
- **Model**: Granite 4.0 Micro (Q4_K_M quantization)

### Resource Requirements

The deployment is configured with:

**Requests:**
- Memory: 6 GB
- CPU: 2 cores

**Limits:**
- Memory: 12 GB
- CPU: 4 cores

Adjust these in `granite-deploy.yaml` based on your cluster capacity.

## Integration with RAG Backend

The RAG backend automatically uses the Granite service when configured with:

```yaml
env:
  - name: GRANITE_HOST
    value: "granite-service"
  - name: GRANITE_PORT
    value: "8080"
```

The backend's query classifier determines when to use Granite vs TinyLlama:
- **TinyLlama**: Simple lifecycle queries (Part 1 & 2)
- **Granite**: Complex technical questions, sales queries, multi-step reasoning

## Testing

### Health Check

```bash
# Get the route URL
GRANITE_URL=$(oc get route granite-service -o jsonpath='{.spec.host}')

# Test health endpoint
curl https://$GRANITE_URL/health
```

### Test Query

```bash
# Test with a simple completion
curl -X POST https://$GRANITE_URL/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the key features of IBM Power10 processors?",
    "n_predict": 100
  }'
```

## Troubleshooting

### Pod Not Starting

Check pod logs:
```bash
oc logs -f deployment/granite-service
```

Common issues:
- Insufficient memory (increase limits)
- Node selector not matching (check MMA support)
- Model download failed (check network connectivity)

### Service Not Responding

Check service endpoints:
```bash
oc get endpoints granite-service
```

Verify the pod is ready:
```bash
oc get pods -l app=granite-service
```

### Performance Issues

If responses are slow:
1. Check CPU/memory usage: `oc adm top pods`
2. Increase thread count in Dockerfile (line 61)
3. Consider using a smaller quantization (Q3_K_M)

## Model Information

**Granite 4.0 Micro**
- Size: ~2.5 GB (Q4_K_M quantization)
- Parameters: ~4B
- Context: 4096 tokens
- Source: [HuggingFace](https://huggingface.co/ibm-granite/granite-4.0-micro-GGUF)

## Comparison with TinyLlama

| Feature | TinyLlama | Granite 4.0 Micro |
|---------|-----------|-------------------|
| Size | 1.1B params | 4B params |
| Use Case | Simple demos | Complex RAG |
| Memory | 2-4 GB | 6-12 GB |
| Accuracy | Basic | High |
| Speed | Fast | Moderate |

## Next Steps

After deploying the Granite service:

1. **Update RAG Backend**: Ensure `GRANITE_HOST=granite-service` is set
2. **Test Complex Queries**: Try questions that require reasoning
3. **Monitor Performance**: Watch resource usage and response times
4. **Tune Parameters**: Adjust context window and threads as needed

## Related Documentation

- [Part3 Deployment Guide](../DEPLOYMENT_GUIDE.md)
- [RAG Backend Configuration](../rag-backend/README.md)
- [Query Classification](../rag-backend/query_classifier.py)