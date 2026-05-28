# OpenSearch Image Authentication Issue - Critical Fix

## Problem Summary

When deploying OpenSearch on IBM Power OpenShift, using the wrong IBM Container Registry namespace causes authentication failures.

## ❌ WRONG - Will Fail

```yaml
image: icr.io/ibm/opensearch:3.3.0
```

**Error:** `ImagePullBackOff` - Authentication required

**Reason:** The `icr.io/ibm/*` namespace requires image pull secrets for authentication.

## ✅ CORRECT - Works Without Authentication

```yaml
image: icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0
```

**Success:** Image pulls without authentication

**Reason:** The `icr.io/ppc64le-oss/*` namespace provides unauthenticated access to Power-optimized open-source images.

## IBM Container Registry Namespaces

| Namespace | Authentication | Use Case | Example |
|-----------|---------------|----------|---------|
| `icr.io/ibm/*` | ✅ Required | IBM proprietary images | `icr.io/ibm/opensearch:3.3.0` |
| `icr.io/ppc64le-oss/*` | ❌ Not required | Power-optimized OSS images | `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` |

## Rule for OpenShift Deployments

**Always use `icr.io/ppc64le-oss/*` namespace for Power-optimized open-source images in OpenShift.**

This avoids the need to:
- Create image pull secrets
- Configure service accounts
- Manage IBM Cloud API keys
- Deal with authentication failures

## Available OpenSearch Versions

All available in the `ppc64le-oss` namespace without authentication:

- `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` (recommended)
- `icr.io/ppc64le-oss/opensearch-ppc64le:2.11.1`
- `icr.io/ppc64le-oss/opensearch-ppc64le:2.9.0`

## How We Discovered This

1. **Initial deployment** used `icr.io/ibm/opensearch:3.3.0`
2. **Result:** ImagePullBackOff error
3. **Investigation:** Checked pod events, found authentication error
4. **Research:** Found IBM Community blog about Power OSS images
5. **Solution:** Changed to `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0`
6. **Result:** ✅ Successful deployment without authentication

## References

- [IBM Community Blog: Open Source Containers for Power in ICR](https://community.ibm.com/community/user/blogs/priya-seth/2023/04/05/open-source-containers-for-power-in-icr)
- [OpenSearch Documentation](https://opensearch.org/docs/latest/)
- [IBM Container Registry](https://icr.io)

## Files Updated

1. `opensearch-deployment/opensearch-deploy.yaml` - Changed image to `ppc64le-oss` namespace
2. `opensearch-deployment/README.md` - Documented the namespace difference
3. `DEPLOYMENT_FIXES.md` - Added to Key Learnings section

## Impact

This fix is **critical** for:
- ✅ Fresh cluster deployments
- ✅ Automated deployment scripts
- ✅ Documentation accuracy
- ✅ Future troubleshooting

Without this fix, OpenSearch deployment will fail with authentication errors, blocking the entire RAG demo.

---

**Created:** 2026-05-28  
**Severity:** Critical  
**Status:** Resolved  
**Applies to:** All IBM Power OpenShift deployments using OpenSearch