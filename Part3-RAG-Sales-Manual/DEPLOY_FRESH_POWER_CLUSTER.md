# Fresh IBM Power OCP Cluster Deployment - Windows Guide

## Overview

This guide walks you through deploying the IBM Power RAG Sales Manual demo to your **fresh IBM Power OpenShift cluster** using **Windows PowerShell** and **Git Bash** where needed.

**Important**: This cluster is running on IBM Power10 architecture, which is perfect for demonstrating AI workloads on Power.

## 🌟 IBM Power10 AI Capabilities

**This demo runs on IBM Power10 without requiring Spyre or Power11.**

This demonstrates the **IBM Open-Source AI Foundation for Power**, proving that customers can start AI initiatives on their existing Power10 infrastructure today, with a clear migration path to Power11 + Spyre for enhanced performance later.

📖 **See [IBM_POWER_AI_FOUNDATION.md](IBM_POWER_AI_FOUNDATION.md)** for complete details on:
- IBM Project AI Services integration
- Power10 MMA acceleration capabilities
- Migration path to Power11 + Spyre
- Official IBM support and announcements

**Key Message**: *"Start AI on Power10 today. No need to wait for Power11 or Spyre."*

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Fresh IBM Power10 OCP Cluster                  │
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
                  │  Scraper Service│ (External - persists)
                  └─────────────────┘
```

## Prerequisites

### Required Tools
- ✅ **oc CLI** - OpenShift command line tool
- ✅ **Git** - For cloning repository
- ✅ **Git Bash** - For running bash scripts (when needed)
- ✅ **PowerShell** - For Windows-native commands

### Required Access
- ✅ **Fresh IBM Power OCP cluster** (TechZone reservation)
- ✅ **Cluster login credentials** (from TechZone)
- ✅ **GitHub repository access**: https://github.com/DSpurway/IBM-Power-RAG-Demos

### External Services
- ✅ **Code Engine Scraper** (already deployed, won't expire):
  - URL: `https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud`
  - This service scrapes IBM documentation and persists independently

## Pre-Deployment Checklist

Before starting, verify:

- [ ] You have logged into your **new** IBM Power OCP cluster
- [ ] You can run `oc whoami` successfully
- [ ] You have the repository cloned locally
- [ ] You know your cluster's base domain (e.g., `apps.pXXXX.cecc.ihost.com`)

## Step-by-Step Deployment

### Step 0: Verify Prerequisites

**PowerShell:**
```powershell
# Check oc CLI is installed
oc version

# Check you're logged into the NEW cluster
oc whoami
oc cluster-info

# Verify you're on the fresh cluster (not the old one)
oc get nodes
```

**Expected output**: You should see your Power10 node listed (single-node cluster).

### Step 1: Navigate to Project Directory

**PowerShell:**
```powershell
# Navigate to the project directory
cd C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual

# Verify you're in the right place
Get-ChildItem -Name deploy-fresh-cluster.sh
```

### Step 2: Create OpenShift Project

**PowerShell:**
```powershell
# Create new project
oc new-project rag-demo

# Verify project creation
oc project
```

**Expected output**: `Using project "rag-demo" on server "https://..."`

### Step 3: Deploy OpenSearch (Vector Database)

**IMPORTANT:** OpenSearch uses the **unauthenticated** `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` image. See [OPENSEARCH_IMAGE_CRITICAL_FIX.md](OPENSEARCH_IMAGE_CRITICAL_FIX.md) for details on why this specific image is required.

**PowerShell:**
```powershell
# Navigate to OpenSearch deployment directory
cd opensearch-deployment

# Deploy OpenSearch
oc apply -f opensearch-deploy.yaml
oc apply -f opensearch-svc.yaml

# Wait for OpenSearch to be ready (this may take 2-3 minutes)
oc rollout status deployment/opensearch-service --timeout=10m

# Verify deployment
oc get pods -l app=opensearch-service
```

**Expected output**: Pod should show `1/1 Running`

**Note:** If you see `ImagePullBackOff`, verify the deployment uses `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` (not `icr.io/ibm/opensearch:3.3.0`).

### Step 4: Deploy Granite LLM Service (Part 3)

**PowerShell:**
```powershell
# Navigate to Granite service directory
cd ..\granite-service

# Create build configuration
oc new-build --name=granite-service --binary --strategy=docker

# Start build (this will take 5-10 minutes)
oc start-build granite-service --from-dir=. --follow

# Deploy the service
oc apply -f granite-deploy.yaml
oc apply -f granite-svc.yaml
oc apply -f granite-route.yaml

# Wait for deployment (this takes ~5-10 minutes - large model download)
oc rollout status deployment/granite-service --timeout=15m

# Verify deployment
oc get pods -l app=granite-service
```

**Note**: Granite service downloads a ~4GB model, so this step takes longer.

### Step 5: Deploy TinyLlama LLM Service (Part 1 & 2)

**PowerShell:**
```powershell
# Navigate to TinyLlama service directory
cd ..\llama-cpp-server

# Create build configuration
oc new-build --name=llama-service --binary --strategy=docker

# Start build
oc start-build llama-service --from-dir=. --follow

# Deploy the service
oc apply -f llama-deploy.yaml
oc apply -f llama-svc.yaml
oc apply -f llama-route.yaml

# Wait for deployment
oc rollout status deployment/llama-service --timeout=10m

# Verify deployment
oc get pods -l app=llama-service
```

### Step 6: Deploy RAG Backend (Consolidated)

**PowerShell:**
```powershell
# Navigate to RAG backend directory
cd ..\rag-backend

# Create build configuration
oc new-build --name=rag-backend --binary --strategy=docker

# Start build
oc start-build rag-backend --from-dir=. --follow

# Deploy the service (no route - internal only)
oc apply -f rag-backend-deploy.yaml
oc apply -f rag-backend-svc.yaml

# Configure environment variables
$SCRAPER_URL = "https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud"

oc set env deployment/rag-backend `
  OPENSEARCH_HOST=opensearch-service `
  OPENSEARCH_PORT=9200 `
  GRANITE_HOST=granite-service `
  GRANITE_PORT=8080 `
  TINYLLAMA_HOST=llama-service `
  TINYLLAMA_PORT=8080 `
  SCRAPER_URL=$SCRAPER_URL `
  CORS_ORIGIN='*'

# Wait for deployment
oc rollout status deployment/rag-backend --timeout=10m

# Verify deployment
oc get pods -l app=rag-backend
```

### Step 7: Deploy Carbon RAG UI (Frontend)

**PowerShell:**
```powershell
# Navigate to Carbon UI directory
cd ..\carbon-rag-ui

# Create build configuration
oc new-build --name=carbon-rag-ui --binary --strategy=docker

# Start build
oc start-build carbon-rag-ui --from-dir=. --follow

# Deploy the service
oc apply -f carbon-rag-ui-deploy.yaml
oc apply -f carbon-rag-ui-svc.yaml
oc apply -f carbon-rag-ui-route.yaml

# Configure frontend to use internal backend service
oc set env deployment/carbon-rag-ui `
  RAG_BACKEND_URL=http://rag-backend:8080

# Wait for deployment
oc rollout status deployment/carbon-rag-ui --timeout=10m

# Verify deployment
oc get pods -l app=carbon-rag-ui
```

### Step 8: Get All Service URLs

**PowerShell:**
```powershell
Write-Host "`n=========================================="
Write-Host "Deployment Complete - Service URLs"
Write-Host "==========================================`n"

$UI_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}'

Write-Host "Carbon UI:     https://$UI_URL"
Write-Host "Scraper:       https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud"
Write-Host ""
Write-Host "Internal Services (no external routes):"
Write-Host "  - OpenSearch:    http://opensearch-service:9200"
Write-Host "  - Granite LLM:   http://granite-service:8080"
Write-Host "  - TinyLlama LLM: http://llama-service:8080"
Write-Host "  - RAG Backend:   http://rag-backend:8080"
Write-Host "`n=========================================="
```

### Step 9: Verify All Services

**PowerShell:**
```powershell
# Check all pods are running
Write-Host "`nChecking pod status..."
oc get pods

# Test frontend (which proxies to backend internally)
Write-Host "`nTesting frontend..."
$UI_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}'
curl.exe https://$UI_URL

# Test collections endpoint via frontend API proxy
Write-Host "`nTesting collections endpoint via frontend..."
curl.exe https://$UI_URL/api/rag/collections
```

## Using Git Bash for Complex Commands

If you need to run the automated deployment script (which uses bash syntax), use Git Bash:

**Git Bash:**
```bash
cd /c/Users/029878866/EMEA-AI-SQUAD/RAG-with-Notebook/Part3-RAG-Sales-Manual
chmod +x deploy-fresh-cluster.sh
./deploy-fresh-cluster.sh
```

## Post-Deployment: Load Sales Manuals

### Option 1: Using the UI (Recommended)

1. Open the Carbon UI in your browser:
   ```powershell
   $UI_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}'
   Start-Process "https://$UI_URL"
   ```

2. Navigate to the **Sales Manual** page

3. Click **"Load All Documents"** button

4. Wait for bulk ingestion to complete:
   - **First run**: ~45-60 minutes (full ingestion of 26 servers)
   - **Subsequent runs**: ~5-10 minutes (intelligent skip logic)

### Option 2: Using API (Advanced)

**PowerShell:**
```powershell
# Get backend pod name
$POD = oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}'

# Start bulk ingestion
oc exec $POD -- curl -s -X POST http://localhost:8080/api/start-bulk-ingestion -H "Content-Type: application/json"

# Monitor progress
oc logs -f deployment/rag-backend
```

## Monitoring and Troubleshooting

### Check Pod Status

**PowerShell:**
```powershell
# View all pods
oc get pods

# Check specific service
oc get pods -l app=rag-backend

# View pod logs
oc logs -f deployment/rag-backend
```

### Check Service Health

**PowerShell:**
```powershell
# Test backend
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
curl.exe https://$BACKEND_URL/health

# Test Granite LLM
$GRANITE_URL = oc get route granite-service -o jsonpath='{.spec.host}'
curl.exe https://$GRANITE_URL/health

# Test scraper
curl.exe https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud/health
```

### Monitor Bulk Ingestion

**PowerShell:**
```powershell
# Check ingestion status
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
curl.exe https://$BACKEND_URL/api/bulk-ingestion-status | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Watch backend logs
oc logs -f deployment/rag-backend
```

### Common Issues

#### Pods Not Starting

```powershell
# Check pod events
oc get events --sort-by='.lastTimestamp'

# Describe pod for details
$POD = oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}'
oc describe pod $POD
```

#### Build Failures

```powershell
# Check build logs
oc logs -f bc/rag-backend

# Retry build
oc start-build rag-backend --follow
```

#### Service Not Accessible

```powershell
# Check route
oc get route rag-backend

# Check service endpoints
oc get endpoints rag-backend

# Test internal connectivity (Git Bash)
# oc run test-pod --image=curlimages/curl --rm -it -- curl http://rag-backend:8080/health
```

## Testing the System

### Test Query Examples

Once data is loaded, try these queries in the UI:

1. **"What are the processor options for E1080?"**
2. **"Compare S1022 and S1024 memory configurations"**
3. **"What activations are available for S924?"**
4. **"Tell me about the S1014 server specifications"**

### Verify Data Loading

**PowerShell:**
```powershell
# Check collections
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
curl.exe https://$BACKEND_URL/api/collections

# Check document count for a specific server
curl.exe "https://$BACKEND_URL/api/collections/s924_42a/count"
```

## Resource Requirements

Your fresh IBM Power10 cluster should have:

- **Minimum**: 3 Power10 nodes with MMA support
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

## Differences from Old Cluster

This deployment is **completely fresh** and includes:

✅ **New consolidated architecture** (rag-backend + carbon-rag-ui)  
✅ **Intelligent skip logic** for faster re-ingestion  
✅ **Bulk ingestion status tracking**  
✅ **Improved error handling**  
✅ **Better UI with activation details**  

The old cluster had separate microservices (RAG-List-Collections, RAG-Drop-Collection, etc.) which have been consolidated into the single rag-backend service.

## Next Steps

1. ✅ **Verify all services are running**
2. ✅ **Load sales manuals** (first run ~45-60 minutes)
3. ✅ **Test queries** against the loaded data
4. ✅ **Monitor performance** on IBM Power10
5. ✅ **Demo to customers** showing AI on Power

## Documentation References

- **[FRESH_CLUSTER_DEPLOYMENT.md](FRESH_CLUSTER_DEPLOYMENT.md)** - Complete deployment guide
- **[SKIP_LOGIC_DOCUMENTATION.md](SKIP_LOGIC_DOCUMENTATION.md)** - Intelligent skip logic details
- **[BULK_INGESTION_ENHANCEMENT.md](BULK_INGESTION_ENHANCEMENT.md)** - Bulk ingestion features
- **[GRANITE_SERVICE_DEPLOYMENT.md](GRANITE_SERVICE_DEPLOYMENT.md)** - Granite LLM details
- **[OPENSEARCH_IMAGE_CRITICAL_FIX.md](OPENSEARCH_IMAGE_CRITICAL_FIX.md)** - ⚠️ Critical: OpenSearch image namespace fix
- **[DEPLOYMENT_FIXES.md](DEPLOYMENT_FIXES.md)** - All deployment issues and resolutions

## Support

For issues:
1. Check pod logs: `oc logs -f deployment/<service-name>`
2. Review this documentation
3. Check GitHub repository issues
4. Contact the development team

---

**Created**: 2026-05-28  
**For**: Fresh IBM Power10 OCP Cluster  
**Platform**: Windows with PowerShell  
**Architecture**: Consolidated rag-backend + carbon-rag-ui