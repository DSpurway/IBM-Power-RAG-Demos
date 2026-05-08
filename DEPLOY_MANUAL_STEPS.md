# Manual Deployment Steps

Run these commands from: `C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook`

## Step 1: Commit Code Changes

```powershell
# Add code files (no credentials)
git add Part3-RAG-Sales-Manual/rag-backend/query_classifier.py
git add Part3-RAG-Sales-Manual/rag-backend/watson_assistant_service.py
git add Part3-RAG-Sales-Manual/rag-backend/requirements.txt
git add Part3-RAG-Sales-Manual/rag-backend/WATSON_ASSISTANT_INTEGRATION.md
git add Part3-RAG-Sales-Manual/rag-backend/WATSON_CLARIFICATION_HANDLING.md
git add Part3-RAG-Sales-Manual/rag-backend/DEPLOY_NOW.md
git add WATSON_ASSISTANT_AND_BUG_FIX_SUMMARY.md
git add WATSON_INTEGRATION_COMPLETE.md
git add .gitignore

# Commit
git commit -m "Fix: Enhanced query classifier for 'stop supporting' queries + Watson Assistant integration"

# Push to Git
git push
```

## Step 2: Set Watson Assistant Credentials (in OpenShift)

```powershell
# These go to OpenShift, NOT to Git
oc set env deployment/rag-backend `
  WATSON_ASSISTANT_API_KEY="Y-WtqYpU77yrcm7bs2xHqVKjzm9d6gLUh_4o-B0CChGJ" `
  WATSON_ASSISTANT_URL="https://api.eu-gb.assistant.watson.cloud.ibm.com/instances/c6a8deb1-c724-4ad3-ac1d-660144bf8792" `
  WATSON_ASSISTANT_ID="f4e6efd1-b43a-490f-af40-3f1b7e219c1a"
```

## Step 3: Rebuild Backend

```powershell
# Start new build with updated code from Git
oc start-build rag-backend --follow
```

## Step 4: Wait for Deployment

```powershell
# Wait for rollout to complete
oc rollout status deployment/rag-backend
```

## Step 5: Verify

```powershell
# Check the pods
oc get pods -l app=rag-backend

# Check logs for Watson
oc logs deployment/rag-backend --tail=20 | Select-String -Pattern "watson"
```

## Step 6: Test

```bash
# Test the fixed query
curl -X POST "http://$(oc get route rag-backend -o jsonpath='{.spec.host}')/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "When did we stop supporting the S924?"}'
```

Expected: Fast response with end of support date (no 500 error)

---

**Made with Bob** 🤖