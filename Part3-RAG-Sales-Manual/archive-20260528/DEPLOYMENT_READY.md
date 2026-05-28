# 🎯 Deployment Ready - Fresh IBM Power Cluster

## Status: Ready to Deploy ✅

You now have everything you need to deploy the RAG Sales Manual demo to your fresh IBM Power10 OpenShift cluster.

## 🌟 Important: IBM Power10 AI Capabilities

**This demo runs on IBM Power10 without requiring Spyre or Power11.**

This demonstrates the **IBM Open-Source AI Foundation for Power**, which provides full AI capabilities on Power10-based servers today. You can start your AI journey now and migrate to Power11 with Spyre later for enhanced performance.

📖 **See [IBM_POWER_AI_FOUNDATION.md](IBM_POWER_AI_FOUNDATION.md) for complete details** on:
- Why Power10 is ready for AI workloads today
- IBM Project AI Services integration
- Migration path to Power11 + Spyre
- Official IBM announcements and support

**Key Resources**:
- [IBM Open-Source AI Foundation Announcement](https://www.ibm.com/docs/en/announcements/open-source-ai-foundation-is-now-available-power10-technology-based-servers)
- [IBM Project AI Services](https://github.com/IBM/project-ai-services)
- [Open Source Containers for Power](https://community.ibm.com/community/user/blogs/priya-seth/2023/04/05/open-source-containers-for-power-in-icr)

## 📦 What's Been Prepared

### 1. **Comprehensive Deployment Guide**
- **[DEPLOY_FRESH_POWER_CLUSTER.md](DEPLOY_FRESH_POWER_CLUSTER.md)** - Complete Windows/PowerShell guide
  - Step-by-step instructions
  - Troubleshooting section
  - Monitoring commands
  - Post-deployment testing

### 2. **Automated Deployment Script**
- **[deploy-fresh-cluster.ps1](deploy-fresh-cluster.ps1)** - PowerShell automation
  - Checks prerequisites
  - Deploys all 5 services
  - Configures environment variables
  - Provides verification steps

### 3. **Quick Reference Card**
- **[QUICK_DEPLOY_REFERENCE.md](QUICK_DEPLOY_REFERENCE.md)** - Cheat sheet
  - Quick commands
  - Troubleshooting one-liners
  - Monitoring commands
  - Emergency fixes

## 🚀 How to Deploy

### Option 1: Automated (Recommended)

**PowerShell:**
```powershell
cd C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual
.\deploy-fresh-cluster.ps1
```

This will:
1. ✅ Check prerequisites
2. ✅ Create project
3. ✅ Deploy all services in order
4. ✅ Configure environment variables
5. ✅ Verify deployments
6. ✅ Provide service URLs

**Estimated time**: 25-30 minutes

### Option 2: Manual Step-by-Step

Follow the detailed guide in [DEPLOY_FRESH_POWER_CLUSTER.md](DEPLOY_FRESH_POWER_CLUSTER.md)

Good for:
- Learning the deployment process
- Troubleshooting specific steps
- Customizing the deployment

### Option 3: Git Bash (If Needed)

If you prefer bash or need to run the original script:

```bash
cd /c/Users/029878866/EMEA-AI-SQUAD/RAG-with-Notebook/Part3-RAG-Sales-Manual
chmod +x deploy-fresh-cluster.sh
./deploy-fresh-cluster.sh
```

## 📋 Pre-Deployment Checklist

Before you start, make sure:

- [ ] You're logged into the **NEW** IBM Power cluster (not the old one)
- [ ] You can run `oc whoami` successfully
- [ ] You have the scraper URL: `https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud`
- [ ] You're in the correct directory: `C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual`

**Quick verification:**
```powershell
# Check you're on the right cluster
oc whoami
oc get nodes  # Should show your Power10 node (single-node cluster)

# Check scraper is alive
curl.exe https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud/health
```

## 🏗️ What Gets Deployed

| Service | Purpose | Deploy Time | Resources |
|---------|---------|-------------|-----------|
| **OpenSearch** | Vector database for embeddings | ~2 min | 4GB RAM, 2 CPU |
| **Granite LLM** | Advanced LLM for complex queries | ~10 min | 12GB RAM, 4 CPU |
| **TinyLlama LLM** | Simple LLM for basic demos | ~5 min | 4GB RAM, 2 CPU |
| **RAG Backend** | Consolidated backend service | ~5 min | 4GB RAM, 2 CPU |
| **Carbon UI** | React frontend | ~5 min | 2GB RAM, 1 CPU |

**Total**: ~25-30 minutes, 26GB RAM, 11 CPU cores

## 🎬 After Deployment

### 1. Access the UI

```powershell
$UI_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}'
Start-Process "https://$UI_URL"
```

### 2. Load Sales Manuals

In the UI:
1. Navigate to **Sales Manual** page
2. Click **"Load All Documents"**
3. Wait for completion:
   - **First run**: ~45-60 minutes (26 servers)
   - **Subsequent runs**: ~5-10 minutes (skip logic)

### 3. Test Queries

Try these example queries:
- "What are the processor options for E1080?"
- "Compare S1022 and S1024 memory configurations"
- "What activations are available for S924?"
- "Tell me about the S1014 server specifications"

## 📊 Monitoring Progress

### Watch Deployment
```powershell
# Watch all pods
oc get pods -w

# Follow backend logs
oc logs -f deployment/rag-backend
```

### Check Ingestion Status
```powershell
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
curl.exe https://$BACKEND_URL/api/bulk-ingestion-status
```

## 🔧 Key Configuration

### Scraper Service
- **URL**: `https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud`
- **Location**: IBM Code Engine (external to cluster)
- **Persistence**: Won't expire when cluster expires
- **Purpose**: Scrapes IBM documentation for sales manuals

### Project Name
- **Default**: `rag-demo`
- **Can be changed** in the deployment script

### Environment Variables
All services are pre-configured with:
- Internal service connections (OpenSearch, LLMs)
- External scraper URL
- CORS settings for development

## 🆚 Differences from Old Cluster

Your **new** deployment includes:

✅ **Consolidated Architecture**
- Single `rag-backend` service (vs. 5 separate microservices)
- Single `carbon-rag-ui` frontend (vs. old RAG-Webpage)

✅ **New Features**
- Intelligent skip logic (faster re-ingestion)
- Bulk ingestion status tracking
- Activation details view
- Improved error handling
- Better UI/UX

✅ **Better Performance**
- Fresh Power10 cluster
- Optimized for IBM Power architecture
- No legacy data or configurations

## 🐛 If Something Goes Wrong

### Quick Fixes

**Pod not starting:**
```powershell
oc get pods
oc logs -f deployment/<service-name>
oc describe pod <pod-name>
```

**Build failed:**
```powershell
oc logs -f bc/<service-name>
oc start-build <service-name> --follow
```

**Service not accessible:**
```powershell
oc get route <service-name>
oc get endpoints <service-name>
```

### Full Documentation

See [DEPLOY_FRESH_POWER_CLUSTER.md](DEPLOY_FRESH_POWER_CLUSTER.md) for:
- Detailed troubleshooting
- Common issues and solutions
- Emergency commands
- Resource requirements

## 📚 Documentation Index

1. **[DEPLOY_FRESH_POWER_CLUSTER.md](DEPLOY_FRESH_POWER_CLUSTER.md)** - Complete deployment guide
2. **[QUICK_DEPLOY_REFERENCE.md](QUICK_DEPLOY_REFERENCE.md)** - Quick reference card
3. **[deploy-fresh-cluster.ps1](deploy-fresh-cluster.ps1)** - PowerShell automation script
4. **[deploy-fresh-cluster.sh](deploy-fresh-cluster.sh)** - Bash automation script
5. **[FRESH_CLUSTER_DEPLOYMENT.md](FRESH_CLUSTER_DEPLOYMENT.md)** - Original deployment guide
6. **[SKIP_LOGIC_DOCUMENTATION.md](SKIP_LOGIC_DOCUMENTATION.md)** - Skip logic details
7. **[BULK_INGESTION_ENHANCEMENT.md](BULK_INGESTION_ENHANCEMENT.md)** - Bulk ingestion features

## ✅ Ready to Start?

You're all set! Choose your deployment method:

### Quick Start (Automated)
```powershell
cd C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual
.\deploy-fresh-cluster.ps1
```

### Manual (Step-by-Step)
Open [DEPLOY_FRESH_POWER_CLUSTER.md](DEPLOY_FRESH_POWER_CLUSTER.md) and follow along.

### Need Help?
Check [QUICK_DEPLOY_REFERENCE.md](QUICK_DEPLOY_REFERENCE.md) for quick commands and troubleshooting.

---

## 🎯 Success Criteria

Your deployment is successful when:

- [ ] All 5 pods are running (`oc get pods`)
- [ ] All routes are accessible (`oc get routes`)
- [ ] Backend health check passes
- [ ] UI loads in browser
- [ ] Can click "Load All Documents"
- [ ] Bulk ingestion starts successfully
- [ ] Can query loaded data

## 🚀 Next Steps After Success

1. **Demo to customers** - Show AI running on IBM Power
2. **Test performance** - Compare to x86 deployments
3. **Load more data** - Add custom documents
4. **Customize queries** - Tailor to customer needs
5. **Share results** - Document your success

---

**Status**: Ready to Deploy ✅  
**Created**: 2026-05-28  
**For**: Fresh IBM Power10 OCP Cluster  
**Platform**: Windows with PowerShell  

**Good luck with your deployment! 🎉**