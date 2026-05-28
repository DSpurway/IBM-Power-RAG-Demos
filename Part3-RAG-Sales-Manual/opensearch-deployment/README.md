# OpenSearch Deployment for IBM Power

## Overview

This directory contains the deployment configuration for OpenSearch on IBM Power architecture.

## IBM Power-Optimized Image

**CRITICAL**: This deployment uses the **unauthenticated IBM Power-optimized OpenSearch image** from IBM Container Registry (ICR).

- **Image**: `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0`
- **Namespace**: `ppc64le-oss` (unauthenticated access)
- **Source**: [Open Source Containers for Power in ICR](https://community.ibm.com/community/user/blogs/priya-seth/2023/04/05/open-source-containers-for-power-in-icr)
- **Architecture**: Built specifically for IBM Power (ppc64le)

### Why This Specific Image?

1. **Architecture**: Standard x86 OpenSearch images from Docker Hub **will not work** on IBM Power architecture
2. **Authentication**: Images in `icr.io/ibm/*` namespace **require authentication** and will fail with ImagePullBackOff
3. **Solution**: Use `icr.io/ppc64le-oss/*` namespace which provides **unauthenticated access** to Power-optimized open-source images

### Image Namespace Comparison

| Namespace | Authentication | Example | Status |
|-----------|---------------|---------|--------|
| `icr.io/ibm/opensearch:3.3.0` | ❌ Required | Will fail with ImagePullBackOff | ❌ Don't use |
| `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` | ✅ Not required | Works without credentials | ✅ Use this |

**Lesson Learned**: Always use the `ppc64le-oss` namespace for Power-optimized open-source images on OpenShift to avoid authentication issues.

## Files

- **opensearch-deploy.yaml** - Deployment configuration
  - Uses IBM Power-optimized image
  - Configured for single-node deployment
  - Security plugins disabled for development
  - 4GB memory, 2 CPU cores

- **opensearch-svc.yaml** - Service configuration
  - ClusterIP service (internal access only)
  - Exposes ports 9200 (HTTP) and 9300 (transport)
  - No external route needed

## Deployment

### Manual Deployment

```bash
# Navigate to opensearch-deployment directory
cd opensearch-deployment

# Deploy OpenSearch
oc apply -f opensearch-deploy.yaml
oc apply -f opensearch-svc.yaml

# Wait for deployment
oc rollout status deployment/opensearch-service --timeout=10m

# Verify
oc get pods -l app=opensearch-service
```

### Automated Deployment

The PowerShell deployment script handles this automatically:

```powershell
.\deploy-fresh-cluster.ps1
```

## Configuration

### Environment Variables

- `discovery.type=single-node` - Single-node cluster mode
- `OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g` - 2GB heap size
- `DISABLE_SECURITY_PLUGIN=true` - Security disabled for development
- `DISABLE_INSTALL_DEMO_CONFIG=true` - No demo configuration

### Resources

- **Memory**: 4GB (request and limit)
- **CPU**: 2 cores (request and limit)
- **Storage**: EmptyDir volume (ephemeral)

## Access

OpenSearch is accessed **internally** by the rag-backend service:

- **Service Name**: `opensearch-service`
- **Port**: 9200 (HTTP)
- **URL**: `http://opensearch-service:9200`

No external route is created - OpenSearch is only accessible within the cluster.

## Verification

### From within the cluster

```bash
# Get a pod name
POD=$(oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

# Test OpenSearch from backend pod
oc exec $POD -- curl -s http://opensearch-service:9200

# Check cluster health
oc exec $POD -- curl -s http://opensearch-service:9200/_cluster/health
```

### Check logs

```bash
oc logs -f deployment/opensearch-service
```

## Troubleshooting

### Pod not starting

```bash
# Check pod status
oc get pods -l app=opensearch-service

# Check events
oc describe pod -l app=opensearch-service

# Check logs
oc logs -l app=opensearch-service
```

### Common Issues

1. **Image pull errors**: Ensure you're using the IBM Power image from ICR
2. **Memory issues**: Single-node cluster may need resource adjustments
3. **Startup timeout**: OpenSearch can take 2-3 minutes to start

## Available Versions

IBM Container Registry provides multiple OpenSearch versions for Power in the `ppc64le-oss` namespace:

- `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` (current - unauthenticated)
- `icr.io/ppc64le-oss/opensearch-ppc64le:2.11.1` (unauthenticated)
- `icr.io/ppc64le-oss/opensearch-ppc64le:2.9.0` (unauthenticated)

**Note**: The `icr.io/ibm/*` namespace versions require authentication and should not be used for OpenShift deployments without proper image pull secrets.

See the [IBM Community blog post](https://community.ibm.com/community/user/blogs/priya-seth/2023/04/05/open-source-containers-for-power-in-icr) for the complete list.

## Production Considerations

For production deployments, consider:

1. **Enable security plugins** - Remove `DISABLE_SECURITY_PLUGIN`
2. **Persistent storage** - Replace emptyDir with PVC
3. **Multi-node cluster** - Remove `discovery.type=single-node`
4. **Resource tuning** - Adjust memory/CPU based on workload
5. **Backup strategy** - Implement snapshot/restore

## References

- [IBM Open Source Containers for Power](https://community.ibm.com/community/user/blogs/priya-seth/2023/04/05/open-source-containers-for-power-in-icr)
- [OpenSearch Documentation](https://opensearch.org/docs/latest/)
- [IBM Container Registry](https://icr.io)

---

**Created**: 2026-05-28
**Updated**: 2026-05-28
**For**: IBM Power10 OpenShift Cluster
**Image**: `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` (unauthenticated)