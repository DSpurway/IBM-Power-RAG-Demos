# Deploy Activation Feature Improvements - Simple Commands

## Option 1: Build from Local Directory (Recommended for Testing)

```powershell
cd Part3-RAG-Sales-Manual\rag-backend

# Build new image from local code
oc start-build rag-backend --from-dir=. --follow

# Restart deployment to use new image
oc rollout restart deployment/rag-backend

# Wait for rollout to complete
oc rollout status deployment/rag-backend

# Check pod status
oc get pods -l app=rag-backend

# View logs
oc logs -f deployment/rag-backend
```

## Option 2: Build from GitHub (Recommended for Production)

```powershell
cd Part3-RAG-Sales-Manual\rag-backend

# Commit and push changes
git add activation_feature_service.py
git add *.md
git commit -m "Improve activation feature extraction - match Sales Manual format"
git push

# Trigger rebuild from GitHub
oc start-build rag-backend --follow

# Restart deployment
oc rollout restart deployment/rag-backend

# Wait for rollout
oc rollout status deployment/rag-backend

# Check status
oc get pods -l app=rag-backend
```

## Test the Changes

```powershell
# Get backend URL
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'

# Test health
curl "https://$BACKEND_URL/health"

# Test activation query (replace collection name)
$body = @{
    question = "What activations are available?"
    collection_name = "rag_<your_collection>"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://$BACKEND_URL/api/search" -Method Post -Body $body -ContentType "application/json" -SkipCertificateCheck
```

## What Changed

- **File:** `activation_feature_service.py`
- **Change:** Simplified manual extraction to match IBM Sales Manual format
- **Result:** Clean, single-line descriptions without artifacts

## Expected Output

**Before:**
```
#EPS2: Feature Code: #EPS2 Name: 1 core Base Proc Act (Pools 2.0) for #EDP4 any OS (from Static) | Attributes provided: One Base processor core activation...
```

**After:**
```
#EPS2: 1 core Base Proc Act (Pools 2.0) for #EDP4 any OS
```

## Troubleshooting

If build fails:
```powershell
# Check build logs
oc logs -f bc/rag-backend

# Check if BuildConfig exists
oc get bc rag-backend

# If missing, create it
oc new-build --name=rag-backend --binary --strategy=docker
```

If pod doesn't start:
```powershell
# Check pod logs
oc logs -l app=rag-backend

# Check events
oc get events --sort-by='.lastTimestamp'

# Describe pod
oc describe pod -l app=rag-backend