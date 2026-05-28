# Deployment Fixes for IBM Power10 OpenShift

## Issues Identified and Fixed

### 1. Node Selector Issue - Granite Service
**Problem:** The granite-service deployment had a nodeSelector requiring `feature.node.kubernetes.io/cpu-cpuid.MMA: "true"`, but the Power10 node didn't have this label set, causing pods to remain in Pending state.

**Fix:** Removed the nodeSelector from `granite-service/granite-deploy.yaml`
```yaml
# Before:
nodeSelector:
  feature.node.kubernetes.io/cpu-cpuid.MMA: "true"

# After:
# Node selector removed - not all Power10 nodes have MMA label set
# MMA is available on Power10, but label may not be configured
```

**Status:** ✅ Fixed - Granite pods now running

### 2. Image Pull Issue - Internal Registry
**Problem:** Deployments were using `image: service-name:latest` which defaults to pulling from Docker Hub, causing ImagePullBackOff errors. The images are built in OpenShift's internal registry and need to reference that registry.

**Fix:** Updated image references in deployment files to use the internal OpenShift registry:

**Files Updated:**
- `granite-service/granite-deploy.yaml`
- `rag-backend/rag-backend-deploy.yaml`

```yaml
# Before:
image: granite-service:latest
imagePullPolicy: IfNotPresent

# After:
image: image-registry.openshift-image-registry.svc:5000/rag-demo/granite-service:latest
imagePullPolicy: Always
```

**Status:** ✅ Fixed - Images now pull from internal registry

### 3. OpenSearch Deployment for IBM Power
**Problem:** OpenSearch deployment files were missing, needed Power-specific image.

**Initial Attempt:** Created `opensearch-deployment/opensearch-deploy.yaml` using:
```yaml
image: icr.io/ibm/opensearch:3.3.0  # ❌ WRONG - Requires authentication
```

**Result:** ImagePullBackOff error - authentication required for `icr.io/ibm/*` namespace

**Final Fix:** Changed to unauthenticated Power-optimized image:
```yaml
image: icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0  # ✅ CORRECT - No auth required
```

**Status:** ✅ Fixed - OpenSearch running successfully

**Critical Learning:** IBM Container Registry has two namespaces for Power images:
- `icr.io/ibm/*` - **Requires authentication** (will fail in OpenShift without image pull secrets)
- `icr.io/ppc64le-oss/*` - **No authentication required** (use this for OpenShift deployments)

## Deployment Progress

### Completed
- ✅ Granite LLM Service build completed
- ✅ Granite pods running (1/1 Ready)
- ✅ Llama LLM Service build completed
- ✅ OpenSearch deployment files created

### In Progress
- 🔄 RAG Backend build running (installing Python dependencies)

### Pending
- ⏳ Llama service deployment
- ⏳ RAG Backend deployment
- ⏳ Carbon RAG UI deployment
- ⏳ Service verification
- ⏳ System testing

## Key Learnings

1. **IBM Power10 Node Labels:** Not all Power10 nodes have the MMA feature label set, even though the hardware supports it. Avoid hard-coding nodeSelectors for MMA unless you've verified the label exists.

2. **OpenShift Image References:** When using BuildConfigs, always reference the internal registry explicitly:
   - Format: `image-registry.openshift-image-registry.svc:5000/<namespace>/<image-name>:<tag>`
   - Use `imagePullPolicy: Always` to ensure latest builds are pulled

3. **IBM Container Registry - CRITICAL:** ⚠️ **Use the correct namespace for Power images:**
   - ❌ **WRONG**: `icr.io/ibm/opensearch:3.3.0` - Requires authentication, will fail with ImagePullBackOff
   - ✅ **CORRECT**: `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` - No authentication required
   - **Rule**: Always use `icr.io/ppc64le-oss/*` namespace for Power-optimized open-source images in OpenShift
   - **Why**: The `ibm` namespace requires image pull secrets, while `ppc64le-oss` provides unauthenticated access

4. **Single-Node Clusters:** Documentation should reflect actual cluster topology (single-node vs multi-node)

## Next Steps for Clean Deployment

1. Verify all deployment YAML files use correct internal registry image references
2. Check for any remaining nodeSelector constraints
3. Ensure all services have proper health checks configured
4. Verify network policies allow internal service communication
5. Test external route for Carbon RAG UI only (backend services should remain internal)

## Files Modified

1. `granite-service/granite-deploy.yaml` - Removed nodeSelector, fixed image reference
2. `rag-backend/rag-backend-deploy.yaml` - Fixed image reference
3. `opensearch-deployment/opensearch-deploy.yaml` - Created with IBM Power image
4. `opensearch-deployment/opensearch-svc.yaml` - Created service definition
5. `opensearch-deployment/README.md` - Added documentation

## Commands for Future Reference

### Check pod status
```bash
oc get pods
```

### Check build status
```bash
oc get builds
```

### Check image streams
```bash
oc get imagestream
```

### Describe pod for troubleshooting
```bash
oc describe pod <pod-name>
```

### Apply updated deployment
```bash
oc apply -f <deployment-file>.yaml
oc rollout restart deployment/<deployment-name>
```

### Monitor build logs
```bash
oc logs -f <build-pod-name>