# Quick Deployment Guide

## Step 1: Login to OpenShift

```bash
# Login to your OCP cluster
oc login --server=<your-ocp-api-url> --token=<your-token>

# Or use username/password
oc login --server=<your-ocp-api-url> -u <username> -p <password>

# Verify you're logged in
oc whoami
oc project
```

## Step 2: Set Watson Assistant Environment Variables

```bash
# Set the Watson Assistant credentials
oc set env deployment/rag-backend \
  WATSON_ASSISTANT_API_KEY="Y-WtqYpU77yrcm7bs2xHqVKjzm9d6gLUh_4o-B0CChGJ" \
  WATSON_ASSISTANT_URL="https://api.eu-gb.assistant.watson.cloud.ibm.com/instances/c6a8deb1-c724-4ad3-ac1d-660144bf8792" \
  WATSON_ASSISTANT_ID="f4e6efd1-b43a-490f-af40-3f1b7e219c1a"

# Verify the environment variables were set
oc set env deployment/rag-backend --list | grep WATSON
```

## Step 3: Rebuild the Backend

```bash
# Start a new build with the updated code
oc start-build rag-backend --follow

# This will:
# - Build the new Docker image with bug fixes
# - Include Watson Assistant integration
# - Deploy the new version
```

## Step 4: Wait for Rollout

```bash
# Wait for the deployment to complete
oc rollout status deployment/rag-backend

# Check the pods are running
oc get pods -l app=rag-backend
```

## Step 5: Verify Deployment

```bash
# Check the logs for Watson Assistant initialization
oc logs -f deployment/rag-backend | grep -i watson

# You should see:
# INFO:query_classifier:Watson Assistant integration available
# INFO:query_classifier:Watson Assistant enabled for query classification
```

## Step 6: Test the Fix

```bash
# Get the backend route
BACKEND_URL=$(oc get route rag-backend -o jsonpath='{.spec.host}')

# Test the previously failing query
curl -X POST "http://$BACKEND_URL/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "When did we stop supporting the S924?"}'

# Should return a successful response with the end of support date
```

## Alternative: Deploy Without Watson (Regex Only)

If you want to deploy just the bug fix without Watson Assistant:

```bash
# Just rebuild without setting Watson environment variables
oc start-build rag-backend --follow
oc rollout status deployment/rag-backend
```

The system will work with regex-based classification (still fixes the bug).

## Troubleshooting

### If build fails:
```bash
# Check build logs
oc logs -f bc/rag-backend

# Check for errors
oc get builds
oc logs build/rag-backend-<build-number>
```

### If pods aren't starting:
```bash
# Check pod status
oc get pods -l app=rag-backend

# Check pod logs
oc logs <pod-name>

# Describe pod for events
oc describe pod <pod-name>
```

### If Watson isn't working:
```bash
# Verify environment variables
oc set env deployment/rag-backend --list | grep WATSON

# Check logs for Watson errors
oc logs deployment/rag-backend | grep -i "watson\|error"
```

## What Gets Fixed

1. **Bug Fix**: "When did we stop supporting the S924?" now works
2. **Watson Integration**: Superior NLP with 98%+ confidence
3. **MTM Extraction**: Recognizes "9080-HEU" format
4. **Graceful Fallback**: Works with or without Watson

## Expected Behavior

### Before Fix:
```
Query: "When did we stop supporting the S924?"
Result: 500 Internal Server Error
```

### After Fix (with Watson):
```
Query: "When did we stop supporting the S924?"
Watson: Check_Date intent (0.983 confidence)
Watson: Lifecycle_date = "EoS", Server_Name = "S924"
Classification: TABLE_LOOKUP
Result: Instant response from lifecycle table
```

### After Fix (without Watson):
```
Query: "When did we stop supporting the S924?"
Regex: Matches "stop supporting" + "S924"
Classification: TABLE_LOOKUP
Result: Instant response from lifecycle table
```

Both work - Watson just provides better NLP!

---

**Made with Bob** 🤖