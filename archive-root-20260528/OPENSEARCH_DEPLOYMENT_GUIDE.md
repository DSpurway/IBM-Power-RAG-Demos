# OpenSearch Deployment Guide for Fresh OCP Cluster

## Overview

This guide walks you through deploying OpenSearch on your fresh IBM Power10 OpenShift cluster. OpenSearch replaces the previous Milvus/ChromaDB setup and provides better compatibility with IBM Power architecture.

## Why OpenSearch?

✅ **No Rust compiler needed** - Eliminates bcrypt build issues  
✅ **No custom SQLite** - Uses standard libraries  
✅ **Better scalability** - Enterprise-grade distributed search  
✅ **Power10 optimized** - Native ppc64le support  
✅ **Proven solution** - Based on IBM project-ai-services  

## Prerequisites

- Fresh OpenShift cluster on IBM Power10
- `oc` CLI installed and logged in
- Project created (e.g., `llm-on-techzone`)

## Deployment Options

You have two deployment options:

### Option 1: Using OpenShift GUI with Custom Dockerfile (Recommended)

This builds OpenSearch from the official ppc64le tarball using the "+" button in OpenShift.

### Option 2: Using OpenShift GUI with Pre-built Image

This uses the pre-built OpenSearch image (may not support ppc64le).

### Option 3: Using CLI

For advanced users who prefer command-line deployment.

---

## Option 1: Deploy Using GUI + Custom Dockerfile (Recommended)

### Step 1: Access Import from Git

1. In OpenShift Console, click the **"+"** button at the top
2. Select **"Import from Git"**

### Step 2: Configure Git Repository

**Git Repo URL**:
```
https://github.com/DSpurway/IBM-Power-RAG-Demos
```

**Show Advanced Git Options** (click to expand):
- **Context dir**: `/Part3-RAG-Sales-Manual/opensearch-deployment`

### Step 3: Configure Build

**Import Strategy**: Should auto-detect as **Dockerfile**

**Dockerfile path**: `Dockerfile` (should be auto-detected)

### Step 4: Configure Application

**Application**:
- Select existing: `ibm-power-rag-demos-app`
- Or create new if this is your first deployment

**Name**: `opensearch-service`

**Resources**:
- Select **Deployment**

**Create a route to the Application**:
- ☐ **Uncheck this** (OpenSearch should not be exposed externally)

### Step 5: Configure Advanced Options

Click **"Show advanced Routing options"** or **"Resource limits"**:

**Resource Limits**:
- CPU Request: `500m`
- CPU Limit: `1`
- Memory Request: `1Gi`
- Memory Limit: `2Gi`

**Target Port**: `9200`

### Step 6: Create

Click **"Create"** button at the bottom

### Step 7: Monitor Build

1. Go to **Builds** in left sidebar
2. Click on `opensearch-service` build
3. Click on **Logs** tab
4. Watch the build progress (5-10 minutes)

Look for:
- Downloading OpenSearch tarball (~200MB)
- Extracting and configuring
- Build complete message

### Step 8: Monitor Deployment

Once build completes:
1. Go to **Topology** view
2. Click on the `opensearch-service` pod
3. Click **Logs** tab
4. Wait for startup (30-60 seconds)

Look for this message:
```
[INFO ][o.o.n.Node] [opensearch-node1] started
```

---

## Option 2: Deploy Using GUI + Pre-built Image

### Step 1: Access Deploy Image

1. In OpenShift Console, click the **"+"** button at the top
2. Select **"Container images"** or **"Deploy Image"**

### Step 2: Configure Image

**Image name from external registry**:
```
opensearchproject/opensearch:2.11.0
```

### Step 3: Configure Application

**Application**: `ibm-power-rag-demos-app`

**Name**: `opensearch-service`

**Create a route**: ☐ **Uncheck**

### Step 4: Set Environment Variables

Click **"Deployment"** section, then add these environment variables:

| Name | Value |
|------|-------|
| `discovery.type` | `single-node` |
| `OPENSEARCH_JAVA_OPTS` | `-Xms512m -Xmx512m` |
| `DISABLE_SECURITY_PLUGIN` | `true` |
| `plugins.security.disabled` | `true` |

### Step 5: Set Resource Limits

- CPU Request: `500m`
- CPU Limit: `1`
- Memory Request: `1Gi`
- Memory Limit: `2Gi`

### Step 6: Create

Click **"Create"**

**Note**: This option may fail if the official image doesn't support ppc64le. If it fails, use Option 1 instead.

---

## Option 3: Deploy Using CLI (Quick Method)

### Step 1: Apply the Deployment YAML

```bash
# Navigate to the opensearch deployment directory
cd Part3-RAG-Sales-Manual/opensearch-deployment

# Apply the simple deployment
oc apply -f opensearch-deploy-simple.yaml
```

This creates:
- **Deployment**: `opensearch-service` (1 replica)
- **Service**: `opensearch-service` (ClusterIP on port 9200)
- **Configuration**: Single-node, security disabled, 512MB heap

---

## Verification Steps (All Options)

After deployment completes, follow these steps to verify OpenSearch is working:

### Step 1: Check Pod Status

**Using GUI**:
1. Go to **Topology** view
2. Click on `opensearch-service` deployment
3. Verify pod shows green checkmark and "Running" status

**Using CLI**:
```bash
oc get pods -l app=opensearch-service
```

Expected output:
```
NAME                                READY   STATUS    RESTARTS   AGE
opensearch-service-xxxxxxxxx-xxxxx   1/1     Running   0          2m
```

### Step 2: Monitor the Logs

**Using GUI**:
1. Click on the pod in Topology view
2. Click **Logs** tab
3. Watch for startup messages

**Using CLI**:

```bash
# Watch the pod start
oc get pods -w -l app=opensearch-service

# Check logs
oc logs -f deployment/opensearch-service
```

**Expected startup time**: 30-60 seconds

Look for this message in logs:
```
[INFO ][o.o.n.Node] [opensearch-node1] started
```

### Step 3: Test OpenSearch Health

**Using GUI Terminal**:
1. In Topology view, click on the `opensearch-service` pod
2. Click **Terminal** tab
3. Run this command:
```bash
curl http://localhost:9200/_cluster/health
```

**Using CLI**:

```bash
# Test from within the cluster
oc exec -it deployment/opensearch-service -- curl http://localhost:9200/_cluster/health

# Expected response:
# {
#   "cluster_name": "opensearch-cluster",
#   "status": "green",
#   "number_of_nodes": 1
# }
```

### Step 4: Test Index Creation

```bash
# Create a test index
oc exec -it deployment/opensearch-service -- curl -X PUT http://localhost:9200/test-index

# List indices
oc exec -it deployment/opensearch-service -- curl http://localhost:9200/_cat/indices
```

---

## Option 2: Deploy Using Custom Dockerfile (If Option 1 Fails)

If the official image doesn't work on ppc64le, use this custom build approach.

### Step 1: Create Build Configuration

```bash
# Navigate to opensearch deployment directory
cd Part3-RAG-Sales-Manual/opensearch-deployment

# Create a new build from the Dockerfile
oc new-build --name=opensearch-service \
  --binary \
  --strategy=docker

# Start the build
oc start-build opensearch-service --from-dir=. --follow
```

**Build time**: 5-10 minutes (downloads ~200MB OpenSearch tarball)

### Step 2: Deploy the Application

```bash
# Create deployment from the built image
oc new-app opensearch-service

# Set resource limits
oc set resources deployment/opensearch-service \
  --requests=memory=1Gi,cpu=500m \
  --limits=memory=2Gi,cpu=1
```

### Step 3: Verify Deployment

```bash
# Check pod status
oc get pods -l app=opensearch-service

# View logs
oc logs -f deployment/opensearch-service

# Test health
oc exec -it deployment/opensearch-service -- curl http://localhost:9200/_cluster/health
```

---

## Configuration Details

### Environment Variables (Already Set in YAML)

| Variable | Value | Description |
|----------|-------|-------------|
| `discovery.type` | single-node | No cluster setup needed |
| `OPENSEARCH_JAVA_OPTS` | -Xms512m -Xmx512m | Heap size for demo |
| `DISABLE_SECURITY_PLUGIN` | true | Simplified auth for demo |
| `plugins.security.disabled` | true | No SSL/TLS required |

### Service Configuration

- **Service Name**: `opensearch-service`
- **Port**: 9200 (HTTP API)
- **Type**: ClusterIP (internal only)
- **No Route**: OpenSearch is not exposed externally (security best practice)

---

## Integration with RAG Backend

Once OpenSearch is running, the RAG backend will connect using these settings:

```yaml
OPENSEARCH_HOST: opensearch-service
OPENSEARCH_PORT: 9200
OPENSEARCH_USERNAME: admin  # Not used when security disabled
OPENSEARCH_PASSWORD: admin  # Not used when security disabled
OPENSEARCH_USE_SSL: false
```

These are already configured in the backend Dockerfile, so no changes needed!

---

## Troubleshooting

### Pod Crashes with OOMKilled

**Symptom**: Pod restarts repeatedly, status shows OOMKilled

**Solution**:
```bash
# Increase memory limits
oc set resources deployment/opensearch-service \
  --requests=memory=2Gi \
  --limits=memory=4Gi
```

### Connection Refused from Backend

**Symptom**: Backend logs show "Connection refused" to OpenSearch

**Check**:
```bash
# Verify service exists
oc get svc opensearch-service

# Verify pod is running
oc get pods -l app=opensearch-service

# Test connectivity from another pod
oc run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://opensearch-service:9200/_cluster/health
```

### Slow Startup

**Symptom**: Pod takes longer than 60 seconds to start

**This is normal!** OpenSearch initialization includes:
- JVM startup
- Plugin loading
- Index recovery
- Cluster state initialization

**Check progress**:
```bash
oc logs -f deployment/opensearch-service
```

Look for these stages:
1. `[INFO ][o.o.e.NodeEnvironment] using [1] data paths`
2. `[INFO ][o.o.d.DiscoveryModule] using discovery type [single-node]`
3. `[INFO ][o.o.n.Node] started` ← **Ready!**

### Build Fails (Option 2 only)

**Symptom**: Build fails to download OpenSearch tarball

**Check**:
```bash
# View build logs
oc logs -f bc/opensearch-service

# Common issues:
# - Network connectivity
# - Tarball URL changed
# - Insufficient build resources
```

**Solution**: Verify the tarball URL is still valid:
```bash
curl -I https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.0/opensearch-2.11.0-linux-ppc64le.tar.gz
```

### Image Pull Errors (Option 1 only)

**Symptom**: `ImagePullBackOff` or `ErrImagePull`

**Possible causes**:
- Official image doesn't support ppc64le
- Network issues pulling from Docker Hub

**Solution**: Switch to Option 2 (custom build)

---

## Verification Checklist

Before proceeding to deploy the RAG backend, verify:

- [ ] OpenSearch pod is running: `oc get pods -l app=opensearch-service`
- [ ] Pod status is `Running` (not `CrashLoopBackOff`)
- [ ] Logs show "started" message
- [ ] Health check returns green status
- [ ] Service exists: `oc get svc opensearch-service`
- [ ] Can create test index successfully

---

## Next Steps

Once OpenSearch is deployed and verified:

1. **Deploy RAG Backend** - See `Part3-RAG-Sales-Manual/rag-backend/OPENSEARCH_QUICK_START.md`
2. **Deploy Frontend** - See `Part3-RAG-Sales-Manual/carbon-rag-ui/README.md`
3. **Deploy LLM Service** - See `Part3-RAG-Sales-Manual/llama-cpp-server/`

---

## Performance Tuning (Optional)

### For Production Use

If you plan to use this beyond a demo:

```bash
# Enable persistent storage
oc set volume deployment/opensearch-service \
  --add --name=opensearch-data \
  --type=persistentVolumeClaim \
  --claim-name=opensearch-pvc \
  --mount-path=/usr/share/opensearch/data

# Scale horizontally (requires cluster mode)
oc scale deployment/opensearch-service --replicas=3

# Increase resources
oc set resources deployment/opensearch-service \
  --requests=memory=4Gi,cpu=2 \
  --limits=memory=8Gi,cpu=4
```

### For Demo Use

Current settings are optimized for demo:
- 512MB heap (sufficient for small datasets)
- Single node (no cluster overhead)
- No persistence (faster startup)
- Security disabled (simplified access)

---

## Monitoring

### Check Resource Usage

```bash
# CPU and memory usage
oc adm top pods -l app=opensearch-service

# Detailed pod info
oc describe pod -l app=opensearch-service
```

### View Metrics

```bash
# OpenSearch cluster stats
oc exec -it deployment/opensearch-service -- \
  curl http://localhost:9200/_cluster/stats?pretty

# Node stats
oc exec -it deployment/opensearch-service -- \
  curl http://localhost:9200/_nodes/stats?pretty
```

---

## Cleanup (If Needed)

To remove OpenSearch and start fresh:

```bash
# Delete deployment and service
oc delete -f opensearch-deploy-simple.yaml

# Or if using custom build:
oc delete all -l app=opensearch-service
oc delete bc/opensearch-service
oc delete is/opensearch-service
```

---

## References

- **OpenSearch Documentation**: https://opensearch.org/docs/latest/
- **IBM project-ai-services**: https://github.com/IBM/project-ai-services
- **OpenSearch Downloads**: https://opensearch.org/downloads.html
- **IBM ppc64le Containers**: https://community.ibm.com/community/user/blogs/priya-seth/2023/04/05/open-source-containers-for-power-in-icr
- **OpenSearch on Power** (by Sumit Dubey): https://community.ibm.com/community/user/blogs/sumit-dubey/2025/06/18/opensearch-an-alternative-to-elasticse
- **Backend Integration Guide**: `Part3-RAG-Sales-Manual/rag-backend/OPENSEARCH_QUICK_START.md`

---

## Support

For issues:
1. Check pod logs: `oc logs -f deployment/opensearch-service`
2. Verify cluster health: `oc exec -it deployment/opensearch-service -- curl http://localhost:9200/_cluster/health`
3. Review this guide's troubleshooting section
4. Check the backend integration guide for connection issues

---

**Version**: 1.0.0  
**Date**: May 1, 2026  
**Based on**: IBM project-ai-services OpenSearch implementation  
**Tested on**: IBM Power10 OpenShift cluster