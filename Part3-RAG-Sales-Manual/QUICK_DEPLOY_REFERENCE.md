# Quick Deploy Reference - Fresh IBM Power Cluster

## 🚀 Quick Start (Automated)

**PowerShell:**
```powershell
cd C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual
.\deploy-fresh-cluster.ps1
```

**Git Bash (if needed):**
```bash
cd /c/Users/029878866/EMEA-AI-SQUAD/RAG-with-Notebook/Part3-RAG-Sales-Manual
chmod +x deploy-fresh-cluster.sh
./deploy-fresh-cluster.sh
```

## 📋 Pre-Flight Checklist

```powershell
# 1. Verify oc CLI
oc version

# 2. Login to NEW cluster (not old one!)
oc login --server=https://your-new-cluster-api:6443

# 3. Verify you're on the right cluster
oc whoami
oc get nodes  # Should show your Power10 node (single-node cluster)

# 4. Check scraper is alive
curl.exe https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud/health
```

## 🎯 Manual Deployment Steps

### Step 1: Create Project
```powershell
oc new-project rag-demo
oc project rag-demo
```

### Step 2: Deploy OpenSearch
```powershell
cd opensearch-deployment
oc apply -f opensearch-deploy.yaml
oc apply -f opensearch-svc.yaml
oc apply -f opensearch-route.yaml
oc rollout status deployment/opensearch-service --timeout=10m
cd ..
```

### Step 3: Deploy Granite LLM
```powershell
cd granite-service
oc new-build --name=granite-service --binary --strategy=docker
oc start-build granite-service --from-dir=. --follow
oc apply -f granite-deploy.yaml
oc apply -f granite-svc.yaml
oc apply -f granite-route.yaml
oc rollout status deployment/granite-service --timeout=15m
cd ..
```

### Step 4: Deploy TinyLlama LLM
```powershell
cd llama-cpp-server
oc new-build --name=llama-service --binary --strategy=docker
oc start-build llama-service --from-dir=. --follow
oc apply -f llama-deploy.yaml
oc apply -f llama-svc.yaml
oc apply -f llama-route.yaml
oc rollout status deployment/llama-service --timeout=10m
cd ..
```

### Step 5: Deploy RAG Backend
```powershell
cd rag-backend
oc new-build --name=rag-backend --binary --strategy=docker
oc start-build rag-backend --from-dir=. --follow
oc apply -f rag-backend-deploy.yaml
oc apply -f rag-backend-svc.yaml
oc apply -f rag-backend-route.yaml

# Configure environment
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

oc rollout status deployment/rag-backend --timeout=10m
cd ..
```

### Step 6: Deploy Carbon UI
```powershell
cd carbon-rag-ui
oc new-build --name=carbon-rag-ui --binary --strategy=docker
oc start-build carbon-rag-ui --from-dir=. --follow
oc apply -f carbon-rag-ui-deploy.yaml
oc apply -f carbon-rag-ui-svc.yaml
oc apply -f carbon-rag-ui-route.yaml

# Configure environment
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
oc set env deployment/carbon-rag-ui NEXT_PUBLIC_API_URL=https://$BACKEND_URL

oc rollout status deployment/carbon-rag-ui --timeout=10m
cd ..
```

## 🔍 Verification Commands

```powershell
# Check all pods
oc get pods

# Get all URLs
$UI_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}'
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
$GRANITE_URL = oc get route granite-service -o jsonpath='{.spec.host}'
$LLAMA_URL = oc get route llama-service -o jsonpath='{.spec.host}'

Write-Host "UI:      https://$UI_URL"
Write-Host "Backend: https://$BACKEND_URL"
Write-Host "Granite: https://$GRANITE_URL"
Write-Host "Llama:   https://$LLAMA_URL"

# Test health endpoints
curl.exe https://$BACKEND_URL/health
curl.exe https://$GRANITE_URL/health
curl.exe https://$LLAMA_URL/health

# Test collections
curl.exe https://$BACKEND_URL/api/collections
```

## 🐛 Troubleshooting Quick Fixes

### Pod Not Starting
```powershell
# Check pod status
oc get pods

# View logs
oc logs -f deployment/rag-backend

# Check events
oc get events --sort-by='.lastTimestamp' | Select-Object -Last 20
```

### Build Failed
```powershell
# Check build logs
oc logs -f bc/rag-backend

# Retry build
oc start-build rag-backend --follow
```

### Service Not Accessible
```powershell
# Check route
oc get route rag-backend

# Check endpoints
oc get endpoints rag-backend

# Describe service
oc describe svc rag-backend
```

### Need to Restart a Service
```powershell
# Restart deployment
oc rollout restart deployment/rag-backend

# Watch rollout
oc rollout status deployment/rag-backend
```

## 📊 Monitoring Commands

```powershell
# Watch pods
oc get pods -w

# Follow backend logs
oc logs -f deployment/rag-backend

# Check ingestion status
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
curl.exe https://$BACKEND_URL/api/bulk-ingestion-status | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Check resource usage
oc adm top pods
oc adm top nodes
```

## 🎬 Post-Deployment Actions

### 1. Open UI
```powershell
$UI_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}'
Start-Process "https://$UI_URL"
```

### 2. Load Sales Manuals
- Click "Load All Documents" in UI
- Wait ~45-60 minutes for first run
- Subsequent runs: ~5-10 minutes (skip logic)

### 3. Test Queries
Try these in the UI:
- "What are the processor options for E1080?"
- "Compare S1022 and S1024 memory configurations"
- "What activations are available for S924?"

## 🔧 Useful One-Liners

```powershell
# Get backend pod name
$POD = oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}'

# Execute command in pod
oc exec $POD -- curl -s http://localhost:8080/health

# Start bulk ingestion from pod
oc exec $POD -- curl -s -X POST http://localhost:8080/api/start-bulk-ingestion -H "Content-Type: application/json"

# Port forward for local testing
oc port-forward deployment/rag-backend 8080:8080

# Delete and redeploy a service
oc delete deployment rag-backend
oc apply -f rag-backend-deploy.yaml
```

## 📝 Important Notes

- **Scraper URL**: `https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud`
- **Project Name**: `rag-demo`
- **Total Deployment Time**: ~25-30 minutes
- **First Data Load**: ~45-60 minutes
- **Subsequent Loads**: ~5-10 minutes (skip logic)

## 🆘 Emergency Commands

```powershell
# Delete everything and start over
oc delete project rag-demo
oc new-project rag-demo

# Force delete stuck pod
oc delete pod <pod-name> --grace-period=0 --force

# Check cluster health
oc get nodes
oc get clusterversion
oc adm top nodes
```

## 📚 Documentation

- **Full Guide**: [DEPLOY_FRESH_POWER_CLUSTER.md](DEPLOY_FRESH_POWER_CLUSTER.md)
- **Skip Logic**: [SKIP_LOGIC_DOCUMENTATION.md](SKIP_LOGIC_DOCUMENTATION.md)
- **Bulk Ingestion**: [BULK_INGESTION_ENHANCEMENT.md](BULK_INGESTION_ENHANCEMENT.md)

---

**Quick Reference Version**: 1.0  
**Last Updated**: 2026-05-28  
**For**: Fresh IBM Power10 OCP Cluster