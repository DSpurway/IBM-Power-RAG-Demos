# Deploy Status Fix - Manual Steps

Run these commands in order from your workspace root directory.

## Step 1: Commit and Push to GitHub

First, sync your local changes to GitHub so the OCP builds can pick them up:

```powershell
# Check what files changed
git status

# Add the changed files
git add Part3-RAG-Sales-Manual/rag-backend/app.py
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/page.js
git add Part3-RAG-Sales-Manual/STATUS_DISPLAY_FIX.md
git add Part3-RAG-Sales-Manual/DEPLOY_STATUS_FIX_STEPS.md

# Commit with a descriptive message
git commit -m "Fix server status display - show actual document counts and filter Harry Potter collection"

# Push to GitHub
git push
```

## Step 2: Trigger Backend Rebuild from GitHub

```powershell
# Trigger a new build from GitHub (OCP will pull the latest code)
oc start-build rag-backend

# Follow the build logs
oc logs -f bc/rag-backend

# Wait for the rollout to complete
oc rollout status deployment/rag-backend --timeout=5m
```

## Step 3: Trigger Frontend Rebuild from GitHub

```powershell
# Trigger a new build from GitHub
oc start-build carbon-rag-ui

# Follow the build logs
oc logs -f bc/carbon-rag-ui

# Wait for the rollout to complete
oc rollout status deployment/carbon-rag-ui --timeout=5m
```

## Step 4: Verify Deployment

```powershell
# Get the frontend URL
oc get route carbon-rag-ui -o jsonpath='{.spec.host}'

# Get the backend URL
oc get route rag-backend -o jsonpath='{.spec.host}'
```

## Step 5: Test

1. Open the frontend URL in your browser (add `https://` prefix)
2. Navigate to the Sales Manual page
3. Click "Refresh Status"
4. You should now see:
   - Accurate "Indexed" status for servers with documents
   - Real document counts in the "Docs" column (e.g., "47" instead of "?")
   - Status message showing total indexed servers and documents
   - Example: "26 servers indexed (1,234 documents)"

## Troubleshooting

If builds fail, check the logs:
```powershell
# Backend logs
oc logs -f deployment/rag-backend

# Frontend logs
oc logs -f deployment/carbon-rag-ui

# Build logs
oc logs -f bc/rag-backend
oc logs -f bc/carbon-rag-ui
```

If you need to check which project you're in:
```powershell
oc project
```

If the build doesn't pick up your changes, verify GitHub sync:
```powershell
# Check your last commit
git log -1

# Verify it's pushed
git status
```

## What Changed

- **Backend**: Now queries OpenSearch for actual document counts and filters out non-Sales Manual collections (like Harry Potter)
- **Frontend**: Displays real document counts and accurate indexing status

---
*Made with Bob - 2026-05-12*