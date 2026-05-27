# Quick Start Guide - Fresh Cluster Deployment

## TL;DR - Deploy Everything

```bash
cd Part3-RAG-Sales-Manual
chmod +x deploy-fresh-cluster.sh
./deploy-fresh-cluster.sh
```

Follow the prompts, then open the UI URL provided at the end.

## What Gets Deployed

| Component | Purpose | Time to Deploy |
|-----------|---------|----------------|
| **OpenSearch** | Vector database for embeddings | ~2 minutes |
| **Granite LLM** | Advanced LLM for complex queries | ~10 minutes |
| **TinyLlama LLM** | Simple LLM for basic demos | ~5 minutes |
| **RAG Backend** | Consolidated backend service | ~5 minutes |
| **Carbon UI** | React frontend | ~5 minutes |

**Total deployment time:** ~25-30 minutes

## Prerequisites

- OpenShift cluster on Power10
- `oc` CLI installed
- Logged into OpenShift: `oc login`
- Scraper service URL (Code Engine - already deployed)

## Step-by-Step (Manual)

### 1. Login and Create Project

```bash
oc login
oc new-project rag-demo
```

### 2. Deploy Services

```bash
cd Part3-RAG-Sales-Manual

# OpenSearch
cd opensearch-deployment
oc apply -f opensearch-deploy.yaml
oc apply -f opensearch-svc.yaml
oc apply -f opensearch-route.yaml
oc rollout status deployment/opensearch-service

# Granite LLM
cd ../granite-service
oc new-build --name=granite-service --binary --strategy=docker
oc start-build granite-service --from-dir=. --follow
oc apply -f granite-deploy.yaml
oc apply -f granite-svc.yaml
oc apply -f granite-route.yaml
oc rollout status deployment/granite-service

# TinyLlama LLM
cd ../llama-cpp-server
oc new-build --name=llama-service --binary --strategy=docker
oc start-build llama-service --from-dir=. --follow
oc apply -f llama-deploy.yaml
oc apply -f llama-svc.yaml
oc apply -f llama-route.yaml
oc rollout status deployment/llama-service

# RAG Backend
cd ../rag-backend
oc new-build --name=rag-backend --binary --strategy=docker
oc start-build rag-backend --from-dir=. --follow
oc apply -f rag-backend-deploy.yaml
oc apply -f rag-backend-svc.yaml
oc apply -f rag-backend-route.yaml

# Configure backend
oc set env deployment/rag-backend \
  OPENSEARCH_HOST=opensearch-service \
  OPENSEARCH_PORT=9200 \
  GRANITE_HOST=granite-service \
  GRANITE_PORT=8080 \
  TINYLLAMA_HOST=llama-service \
  TINYLLAMA_PORT=8080 \
  SCRAPER_URL=https://your-scraper-url.code-engine.appdomain.cloud \
  CORS_ORIGIN='*'

oc rollout status deployment/rag-backend

# Carbon UI
cd ../carbon-rag-ui
oc new-build --name=carbon-rag-ui --binary --strategy=docker
oc start-build carbon-rag-ui --from-dir=. --follow
oc apply -f carbon-rag-ui-deploy.yaml
oc apply -f carbon-rag-ui-svc.yaml
oc apply -f carbon-rag-ui-route.yaml

BACKEND_URL=$(oc get route rag-backend -o jsonpath='{.spec.host}')
oc set env deployment/carbon-rag-ui NEXT_PUBLIC_API_URL=https://$BACKEND_URL

oc rollout status deployment/carbon-rag-ui
```

### 3. Get URLs

```bash
echo "UI: https://$(oc get route carbon-rag-ui -o jsonpath='{.spec.host}')"
echo "Backend: https://$(oc get route rag-backend -o jsonpath='{.spec.host}')"
```

### 4. Load Data

1. Open UI in browser
2. Go to Sales Manual page
3. Click "Load All Documents"
4. Wait ~45-60 minutes for first ingestion

## Scraper Service

The scraper is deployed on IBM Code Engine (external to OpenShift).

### Check Scraper Status

```bash
curl https://your-scraper-url.code-engine.appdomain.cloud/health
```

**Expected response:**
```json
{"status": "healthy", "version": "1.0"}
```

### If Scraper Not Available

The scraper service URL should be provided. If you need to deploy a new one:

1. Log into IBM Cloud
2. Navigate to Code Engine
3. Create application from GitHub:
   - Repo: `https://github.com/DSpurway/IBM-Power-RAG-Demos`
   - Context: `Part3-RAG-Sales-Manual/scraper-test`
   - Port: 5000

## Verification

```bash
# Check all pods running
oc get pods

# Test backend health
curl https://$(oc get route rag-backend -o jsonpath='{.spec.host}')/health

# Test collections endpoint
curl https://$(oc get route rag-backend -o jsonpath='{.spec.host}')/api/collections
```

## Common Issues

### Pods Not Starting

```bash
# Check pod status
oc get pods

# Check logs
oc logs -f deployment/rag-backend

# Check events
oc get events --sort-by='.lastTimestamp'
```

### Build Failures

```bash
# Check build logs
oc logs -f bc/rag-backend

# Retry build
oc start-build rag-backend --follow
```

### Service Not Accessible

```bash
# Check route
oc get route rag-backend

# Test internal connectivity
oc run test --image=curlimages/curl --rm -it -- curl http://rag-backend:8080/health
```

## Next Steps After Deployment

1. **Load Sales Manuals**
   - Click "Load All Documents" in UI
   - First run: ~45-60 minutes
   - Subsequent runs: ~5-10 minutes (skip logic)

2. **Test Queries**
   - Try: "What are the processor options for E1080?"
   - Try: "Compare S1022 and S1024 memory configurations"
   - Try: "What activations are available for S924?"

3. **Monitor Progress**
   ```bash
   # Backend logs
   oc logs -f deployment/rag-backend | grep "Bulk Ingestion"
   
   # Status API
   curl https://$(oc get route rag-backend -o jsonpath='{.spec.host}')/api/bulk-ingestion-status | jq
   ```

## Documentation

- **[FRESH_CLUSTER_DEPLOYMENT.md](FRESH_CLUSTER_DEPLOYMENT.md)** - Complete deployment guide
- **[SKIP_LOGIC_DOCUMENTATION.md](SKIP_LOGIC_DOCUMENTATION.md)** - Intelligent skip logic
- **[BULK_INGESTION_ENHANCEMENT.md](BULK_INGESTION_ENHANCEMENT.md)** - Bulk ingestion features
- **[GRANITE_SERVICE_DEPLOYMENT.md](GRANITE_SERVICE_DEPLOYMENT.md)** - Granite LLM details

## Resource Requirements

**Minimum cluster:**
- 3 Power10 nodes with MMA support
- 48 GB total memory
- 12 total CPU cores

**Per service:**
- OpenSearch: 4 GB RAM, 2 CPU
- Granite LLM: 12 GB RAM, 4 CPU
- TinyLlama: 4 GB RAM, 2 CPU
- Backend: 4 GB RAM, 2 CPU
- Frontend: 2 GB RAM, 1 CPU

## Support

For issues:
1. Check logs: `oc logs -f deployment/<service>`
2. Review documentation
3. Check GitHub issues

---

**Quick Start Version**: 1.0  
**Last Updated**: 2026-05-27