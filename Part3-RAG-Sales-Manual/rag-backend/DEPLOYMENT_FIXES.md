# RAG Backend Deployment - Common Issues and Fixes

## Overview
This document describes two critical issues that have occurred multiple times during backend rebuilds and how to prevent them.

## Issue 1: Missing Watson Assistant Credentials

### Problem
After rebuilding or redeploying the backend, Watson Assistant queries fail with 404 errors:
```
ERROR:watson_assistant_service:Watson Assistant API error: 404 Client Error: Not Found
```

### Root Cause
The deployment YAML was missing the `envFrom` section that loads Watson Assistant credentials from the Kubernetes secret.

### Solution
The deployment YAML **MUST** include the `envFrom` section in the container spec:

```yaml
spec:
  containers:
    - name: rag-backend
      envFrom:
        # Load Watson Assistant credentials from secret
        - secretRef:
            name: watson-assistant-env
      env:
        # ... other environment variables
```

### Verification
Check that the pod has Watson Assistant environment variables:
```bash
oc exec <pod-name> -- env | grep WATSON
```

Expected output:
```
WATSON_ASSISTANT_URL=https://api.eu-gb.assistant.watson.cloud.ibm.com
WATSON_ASSISTANT_API_KEY=<key>
WATSON_ASSISTANT_ID=<id>
```

## Issue 2: Missing Pod Labels (Service Cannot Route Traffic)

### Problem
The UI cannot connect to the backend. Backend logs show no activity even though the pod is running.

### Root Cause
The pod template labels were missing the `app: rag-backend` label. The service selector requires BOTH labels:
- `app: rag-backend`
- `deployment: rag-backend`

But the pod only had `deployment: rag-backend`.

### Solution
The deployment YAML **MUST** include BOTH labels in the pod template:

```yaml
spec:
  selector:
    matchLabels:
      app: rag-backend
      deployment: rag-backend
  template:
    metadata:
      labels:
        app: rag-backend          # CRITICAL: Must match service selector
        deployment: rag-backend   # CRITICAL: Must match service selector
```

### Verification
Check that the pod has both labels:
```bash
oc get pods -l deployment=rag-backend --show-labels
```

Expected output should include: `app=rag-backend,deployment=rag-backend`

Check that the service has endpoints:
```bash
oc get endpoints rag-backend
```

Expected output should show an IP address and port (e.g., `10.128.1.137:8080`).

## Quick Fix Commands

If you encounter these issues after a deployment:

### Fix Missing Watson Assistant Credentials
```bash
oc patch deployment rag-backend --type=json -p='[{"op": "add", "path": "/spec/template/spec/containers/0/envFrom", "value": [{"secretRef": {"name": "watson-assistant-env"}}]}]'
```

### Fix Missing App Label
```bash
oc patch deployment rag-backend --type=json -p='[{"op": "add", "path": "/spec/template/metadata/labels/app", "value": "rag-backend"}]'
```

## Prevention

### Before Deploying
Always verify the deployment YAML has:
1. ✅ `envFrom` section with Watson Assistant secret reference
2. ✅ Both `app` and `deployment` labels in pod template
3. ✅ Matching labels in service selector

### After Deploying
Run these verification commands:
```bash
# Check pod labels
oc get pods -l deployment=rag-backend --show-labels

# Check service endpoints
oc get endpoints rag-backend

# Check Watson Assistant credentials
oc exec $(oc get pods -l deployment=rag-backend -o name | head -1) -- env | grep WATSON

# Check backend logs for activity
oc logs -f $(oc get pods -l deployment=rag-backend -o name | head -1)
```

## Deployment Checklist

Before any backend deployment or rebuild:

- [ ] Verify `rag-backend-deploy.yaml` has `envFrom` section
- [ ] Verify `rag-backend-deploy.yaml` has both labels in pod template
- [ ] Verify Watson Assistant secret exists: `oc get secret watson-assistant-env`
- [ ] After deployment, verify pod has both labels
- [ ] After deployment, verify service has endpoints
- [ ] After deployment, verify Watson Assistant credentials are loaded
- [ ] Test a query to confirm backend is receiving requests

## Related Files
- `rag-backend-deploy.yaml` - Main deployment configuration
- `watson_assistant_service.py` - Watson Assistant integration
- `query_classifier.py` - Uses Watson Assistant for query classification

## Last Updated
2026-05-15 - Both issues fixed and documented