# OpenSearch Deployment for IBM Power

This directory contains the Dockerfile and configuration for deploying OpenSearch on IBM Power (ppc64le) architecture.

## Acknowledgments

This implementation is based on the **IBM Open-Source AI Foundation for Power**, specifically the [IBM project-ai-services](https://github.com/IBM/project-ai-services) OpenSearch deployment.

The IBM Open-Source AI Foundation for Power ([documentation](https://www.ibm.com/docs/en/aiservices)) provides optimized AI services for IBM Power systems. While these services are optimized for IBM Spyre™ on Power, this deployment adapts them for use on **standard OpenShift on Power10 without requiring Spyre**.

## Overview

OpenSearch is used as the vector database for RAG (Retrieval Augmented Generation) functionality in Parts 2 and 3 of the demo.

### Why a Custom Build?

The standard OpenSearch Docker images only support x86_64 architecture. For IBM Power systems, we need to:
1. Download the ppc64le-specific OpenSearch tarball
2. Build a custom container image
3. Configure for single-node development use

## Architecture

- **Base Image**: Red Hat UBI 9 (Universal Base Image)
- **OpenSearch Version**: 2.11.0
- **Java**: OpenJDK 17 (included in UBI)
- **Security**: Disabled for development (simplified authentication)
- **Discovery**: Single-node mode (no cluster setup needed)

## Configuration

### Memory Settings
- **Heap Size**: 512MB min/max (suitable for demo)
- **Memory Lock**: Disabled (works better in containers)

### Network
- **Host**: 0.0.0.0 (listens on all interfaces)
- **Port**: 9200 (HTTP API)
- **Port**: 9300 (Transport - not used in single-node)

### Security
- **Security Plugin**: Disabled
- **Authentication**: None (development only)
- **SSL/TLS**: Disabled

> ⚠️ **Warning**: This configuration is for development/demo only. Production deployments should enable security features.

## Deployment to OpenShift

### Using Import from Git

1. **Click "+" → "Import from Git"**

2. **Git Repository**:
   ```
   https://github.com/DSpurway/IBM-Power-RAG-Demos
   ```

3. **Advanced Git Options**:
   - Context dir: `/Part3-RAG-Sales-Manual/opensearch-deployment`

4. **Application Settings**:
   - Application: `ibm-power-rag-demos-app`
   - Name: `opensearch-service`
   - Target port: 9200
   - Create route: ☐ No (internal access only)

5. **Resources** (Recommended):
   - Memory: 1Gi request, 2Gi limit
   - CPU: 500m request, 1 core limit
   - Storage: 10Gi persistent volume (optional for persistence)

### Build Time

- **Expected**: 5-10 minutes
- **Download**: ~200MB OpenSearch tarball
- **Extract**: Unpack and configure

## Testing

### Health Check
```bash
oc exec -it deployment/opensearch-service -- curl http://localhost:9200/_cluster/health
```

Expected response:
```json
{
  "cluster_name": "opensearch-cluster",
  "status": "green",
  "number_of_nodes": 1
}
```

### Create Test Index
```bash
oc exec -it deployment/opensearch-service -- curl -X PUT http://localhost:9200/test-index
```

### List Indices
```bash
oc exec -it deployment/opensearch-service -- curl http://localhost:9200/_cat/indices
```

## Integration with RAG Backend

The RAG backend expects these environment variables:

```yaml
OPENSEARCH_HOST: opensearch-service
OPENSEARCH_PORT: 9200
OPENSEARCH_USERNAME: admin  # Not used when security disabled
OPENSEARCH_PASSWORD: admin  # Not used when security disabled
OPENSEARCH_USE_SSL: false
```

## Troubleshooting

### Pod Crashes with OOMKilled
- Increase memory limits
- Check heap size settings in Dockerfile

### Connection Refused
- Verify pod is running: `oc get pods`
- Check service exists: `oc get svc opensearch-service`
- View logs: `oc logs deployment/opensearch-service`

### Slow Startup
- OpenSearch takes 30-60 seconds to start
- Check logs for "started" message
- Health check has 60s start period

### Build Fails
- Verify ppc64le tarball is available from artifacts.opensearch.org
- Check network connectivity
- Review build logs for specific errors

## References

- [OpenSearch Documentation](https://opensearch.org/docs/latest/)
- [IBM project-ai-services](https://github.com/IBM/project-ai-services)
- [OpenSearch Downloads](https://opensearch.org/downloads.html)