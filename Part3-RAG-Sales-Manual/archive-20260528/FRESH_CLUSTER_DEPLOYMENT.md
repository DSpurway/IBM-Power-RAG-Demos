# Fresh OpenShift Cluster Deployment Guide

## Overview

Complete guide for deploying the IBM Power RAG Sales Manual demo to a fresh OpenShift cluster. This guide covers the **current consolidated architecture** with rag-backend and carbon-rag-ui.

## Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenShift Cluster                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  OpenSearch  │  │ Granite LLM  │  │ TinyLlama    │    │
│  │  (Vector DB) │  │ (Part 3)     │  │ (Part 1&2)   │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                  │             │
│         └─────────────────┼──────────────────┘             │
│                           │                                │
│                  ┌────────▼────────┐                       │
│                  │   RAG Backend   │                       │
│                  │  (Consolidated) │                       │
│                  └────────┬────────┘                       │
│                           │                                │
│                  ┌────────▼────────┐                       │
│                  │  Carbon RAG UI  │                       │
│                  │   (Frontend)    │                       │
│                  └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
                           │
                  ┌────────▼────────┐
                  │  Code Engine    │
                  │  Scraper Service│ (External - doesn't expire)
                  └─────────────────┘
```

## Prerequisites

### Required
- **OpenShift cluster** on Power10 (TechZone "OpenShift on POWER10")
- **oc CLI** installed and configured
- **Git** installed
- **GitHub repository** access: https://github.com/DSpurway/IBM-Power-RAG-Demos

### Optional
- **Code Engine scraper** (already deployed, won't expire with cluster)
- **Local scraper** (Windows laptop with Python)

## Pre-Deployment Checklist

- [ ] OpenShift cluster provisioned and accessible
- [ ] Logged into OpenShift: `oc login`
- [ ] GitHub repository cloned locally
- [ ] Note your cluster's base domain (e.g., `apps.p1265.cecc.ihost.com`)
- [ ] Scraper service URL available

## Deployment Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/DSpurway/IBM-Power-RAG-Demos.git
cd IBM-Power-RAG-Demos/Part3-RAG-Sales-Manual
```

### Step 2: Create OpenShift Project

```bash
# Create project (if not exists)
oc new-project rag-demo

# Or use existing project
oc project rag-demo
```

### Step 3: Deploy OpenSearch (Vector Database)

```bash
cd opensearch-deployment

# Deploy OpenSearch
oc apply -f opensearch-deploy.yaml
oc apply -f opensearch-svc.yaml
oc apply -f opensearch-route.yaml

# Wait for OpenSearch to be ready
oc rollout status deployment/opensearch-service --timeout=10m

# Verify
oc get pods -l app=opensearch-service
```

**Expected output:**
```
NAME                                 READY   STATUS    RESTARTS   AGE
opensearch-service-xxxxxxxxxx-xxxxx  1/1     Running   0          2m
```

### Step 4: Deploy Granite LLM Service (Part 3)

```bash
cd ../granite-service

# Create build configuration
oc new-build --name=granite-service --binary --strategy=docker

# Build from GitHub
oc start-build granite-service --from-dir=. --follow

# Deploy service
oc apply -f granite-deploy.yaml
oc apply -f granite-svc.yaml
oc apply -f granite-route.yaml

# Wait for deployment (this takes ~5-10 minutes - large model download)
oc rollout status deployment/granite-service --timeout=15m

# Verify
oc get pods -l app=granite-service
GRANITE_URL=$(oc get route granite-service -o jsonpath='{.spec.host}')
curl https://$GRANITE_URL/health
```

**Expected response:** `{"status":"ok"}`

### Step 5: Deploy TinyLlama Service (Part 1 & 2)

```bash
cd ../llama-cpp-server

# Create build configuration
oc new-build --name=llama-service --binary --strategy=docker

# Build from GitHub
oc start-build llama-service --from-dir=. --follow

# Deploy service
oc apply -f llama-deploy.yaml
oc apply -f llama-svc.yaml
oc apply -f llama-route.yaml

# Wait for deployment
oc rollout status deployment/llama-service --timeout=10m

# Verify
oc get pods -l app=llama-service
LLAMA_URL=$(oc get route llama-service -o jsonpath='{.spec.host}')
curl https://$LLAMA_URL/health
```

### Step 6: Deploy RAG Backend (Consolidated)

```bash
cd ../rag-backend

# Create build configuration from GitHub
oc new-app https://github.com/DSpurway/IBM-Power-RAG-Demos \
  --context-dir=Part3-RAG-Sales-Manual/rag-backend \
  --name=rag-backend \
  --strategy=docker

# Wait for build to complete
oc logs -f bc/rag-backend

# Expose service
oc expose svc/rag-backend

# Set environment variables
SCRAPER_URL="https://your-scraper-url.code-engine.appdomain.cloud"

oc set env deployment/rag-backend \
  OPENSEARCH_HOST=opensearch-service \
  OPENSEARCH_PORT=9200 \
  GRANITE_HOST=granite-service \
  GRANITE_PORT=8080 \
  TINYLLAMA_HOST=llama-service \
  TINYLLAMA_PORT=8080 \
  SCRAPER_URL=$SCRAPER_URL \
  CORS_ORIGIN='*'

# Wait for deployment
oc rollout status deployment/rag-backend --timeout=10m

# Verify
oc get pods -l app=rag-backend
BACKEND_URL=$(oc get route rag-backend -o jsonpath='{.spec.host}')
curl https://$BACKEND_URL/health
```

### Step 7: Deploy Carbon RAG UI (Frontend)

```bash
cd ../carbon-rag-ui

# Create build configuration from GitHub
oc new-app https://github.com/DSpurway/IBM-Power-RAG-Demos \
  --context-dir=Part3-RAG-Sales-Manual/carbon-rag-ui \
  --name=carbon-rag-ui \
  --strategy=docker

# Wait for build to complete
oc logs -f bc/carbon-rag-ui

# Expose service
oc expose svc/carbon-rag-ui

# Set environment variables
BACKEND_URL=$(oc get route rag-backend -o jsonpath='{.spec.host}')

oc set env deployment/carbon-rag-ui \
  NEXT_PUBLIC_API_URL=https://$BACKEND_URL

# Wait for deployment
oc rollout status deployment/carbon-rag-ui --timeout=10m

# Verify
oc get pods -l app=carbon-rag-ui
UI_URL=$(oc get route carbon-rag-ui -o jsonpath='{.spec.host}')
echo "UI available at: https://$UI_URL"
```

### Step 8: Verify Scraper Service

The scraper service is deployed on Code Engine and won't expire with the cluster.

```bash
# Test scraper health
curl https://your-scraper-url.code-engine.appdomain.cloud/health

# Expected response: {"status": "healthy", "version": "1.0"}
```

**If scraper is not accessible:**
- Check Code Engine dashboard
- Verify scraper URL in backend environment variables
- See "Scraper Deployment" section below

## Post-Deployment Configuration

### 1. Get All Service URLs

```bash
echo "=== Service URLs ==="
echo "OpenSearch:    https://$(oc get route opensearch-service -o jsonpath='{.spec.host}')"
echo "Granite LLM:   https://$(oc get route granite-service -o jsonpath='{.spec.host}')"
echo "TinyLlama LLM: https://$(oc get route llama-service -o jsonpath='{.spec.host}')"
echo "RAG Backend:   https://$(oc get route rag-backend -o jsonpath='{.spec.host}')"
echo "Carbon UI:     https://$(oc get route carbon-rag-ui -o jsonpath='{.spec.host}')"
```

### 2. Test the System

```bash
# Test backend health
curl https://$(oc get route rag-backend -o jsonpath='{.spec.host}')/health

# Test collections endpoint
curl https://$(oc get route rag-backend -o jsonpath='{.spec.host}')/api/collections

# Open UI in browser
UI_URL=$(oc get route carbon-rag-ui -o jsonpath='{.spec.host}')
echo "Open browser to: https://$UI_URL"
```

### 3. Load Sales Manuals

In the UI:
1. Navigate to the Sales Manual page
2. Click "Load All Documents" button
3. Wait for bulk ingestion to complete (~45-60 minutes for first run)
4. Subsequent runs will use skip logic (~5-10 minutes)

## Quick Deployment Script

For automated deployment, use the provided script:

```bash
cd Part3-RAG-Sales-Manual
./deploy-fresh-cluster.sh
```

This script will:
1. Check prerequisites
2. Deploy all services in order
3. Configure environment variables
4. Verify deployments
5. Provide service URLs

## Scraper Service Deployment (If Needed)

The scraper service is deployed on IBM Code Engine and persists independently of the OpenShift cluster.

### Check Existing Scraper

```bash
# Get scraper URL from backend
oc get deployment rag-backend -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="SCRAPER_URL")].value}'
```

### Deploy New Scraper (If Needed)

See `scraper-test/README.md` for Code Engine deployment instructions.

**Quick steps:**
1. Log into IBM Cloud
2. Create Code Engine project
3. Deploy from GitHub:
   ```bash
   ibmcloud ce application create \
     --name sales-manual-scraper \
     --build-source https://github.com/DSpurway/IBM-Power-RAG-Demos \
     --build-context-dir Part3-RAG-Sales-Manual/scraper-test \
     --port 5000
   ```

## Resource Requirements

### Minimum Cluster Size
- **Nodes**: 3 Power10 nodes with MMA support
- **Total Memory**: 48 GB
- **Total CPU**: 12 cores

### Per-Service Requirements

| Service | Memory | CPU | Storage |
|---------|--------|-----|---------|
| OpenSearch | 4 GB | 2 | 10 GB |
| Granite LLM | 12 GB | 4 | 5 GB |
| TinyLlama LLM | 4 GB | 2 | 2 GB |
| RAG Backend | 4 GB | 2 | 1 GB |
| Carbon UI | 2 GB | 1 | 1 GB |

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
oc get pods

# Check pod logs
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

# Check service endpoints
oc get endpoints rag-backend

# Test internal connectivity
oc run test-pod --image=curlimages/curl --rm -it -- sh
# Inside pod:
curl http://rag-backend:8080/health
```

### OpenSearch Connection Issues

```bash
# Check OpenSearch logs
oc logs -f deployment/opensearch-service

# Test OpenSearch from backend pod
oc exec -it deployment/rag-backend -- curl http://opensearch-service:9200/_cluster/health
```

### LLM Service Issues

```bash
# Check Granite service
oc logs -f deployment/granite-service

# Check TinyLlama service
oc logs -f deployment/llama-service

# Test LLM endpoints
GRANITE_URL=$(oc get route granite-service -o jsonpath='{.spec.host}')
curl https://$GRANITE_URL/health
```

## Verification Checklist

After deployment, verify:

- [ ] All pods are running: `oc get pods`
- [ ] All routes are accessible: `oc get routes`
- [ ] OpenSearch is healthy: `curl https://opensearch-url/_cluster/health`
- [ ] Granite LLM responds: `curl https://granite-url/health`
- [ ] TinyLlama LLM responds: `curl https://tinyllama-url/health`
- [ ] Backend is healthy: `curl https://backend-url/health`
- [ ] UI loads in browser
- [ ] Can click "Load All Documents" in UI
- [ ] Bulk ingestion starts successfully

## Maintenance

### Update Services

```bash
# Rebuild backend from GitHub
oc start-build rag-backend --follow
oc rollout restart deployment/rag-backend

# Rebuild frontend from GitHub
oc start-build carbon-rag-ui --follow
oc rollout restart deployment/carbon-rag-ui
```

### Monitor Resources

```bash
# Check resource usage
oc adm top pods

# Check node resources
oc adm top nodes
```

### Backup Data

```bash
# Backup OpenSearch indices
# (Add backup script here)
```

## Migration from Old Cluster

If migrating from an existing cluster:

1. **Export OpenSearch data** (if needed)
2. **Note scraper URL** (won't change)
3. **Deploy to new cluster** (follow this guide)
4. **Re-ingest data** (use "Load All Documents")
5. **Verify queries work**

## Related Documentation

- [SKIP_LOGIC_DOCUMENTATION.md](SKIP_LOGIC_DOCUMENTATION.md) - Intelligent skip logic
- [BULK_INGESTION_ENHANCEMENT.md](BULK_INGESTION_ENHANCEMENT.md) - Bulk ingestion features
- [STATUS_DISPLAY_FIX.md](STATUS_DISPLAY_FIX.md) - Status display behavior
- [GRANITE_SERVICE_DEPLOYMENT.md](GRANITE_SERVICE_DEPLOYMENT.md) - Granite LLM details

## Support

For issues or questions:
1. Check logs: `oc logs -f deployment/<service-name>`
2. Review documentation in this repository
3. Contact the development team

---

**Created**: 2026-05-27  
**For**: Fresh OpenShift cluster deployment  
**Architecture**: Consolidated rag-backend + carbon-rag-ui