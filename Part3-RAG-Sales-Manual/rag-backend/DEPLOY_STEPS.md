# Smart Chunking Deployment Steps

## Step 1: Commit and Push to GitHub

```powershell
# Navigate to backend directory
cd Part3-RAG-Sales-Manual/rag-backend

# Add new files
git add sales_manual_chunker.py
git add SMART_CHUNKING_DEPLOYMENT.md
git add DEPLOY_STEPS.md

# Add modified files
git add app.py

# Commit with descriptive message
git commit -m "feat: Add smart hierarchical chunking for Sales Manuals

- Add sales_manual_chunker.py with intelligent chunking
- Preserve lifecycle tables as Markdown for direct lookup
- Extract feature codes with metadata
- Update /ingest-scraped-content endpoint
- ~220-320 chunks per server vs 1 massive chunk"

# Push to GitHub
git push origin main
```

## Step 2: Trigger OCP Build

```powershell
# Make sure you're logged into OCP
oc whoami

# Start new build from GitHub
oc start-build rag-backend -n llm-on-techzone --follow
```

## Step 3: Wait for Deployment

```powershell
# Wait for rollout to complete
oc rollout status deployment/rag-backend -n llm-on-techzone
```

## Step 4: Verify Deployment

```powershell
# Check pod is running
oc get pods -n llm-on-techzone | Select-String "rag-backend"

# Check logs for smart chunker
oc logs deployment/rag-backend -n llm-on-techzone --tail=50 | Select-String "sales_manual_chunker"
```

## Step 5: Re-Ingest All Servers

### Option A: Using UI
1. Navigate to Sales Manual page in browser
2. Click "Load All Documents" button
3. Monitor progress (takes 2-4 hours)

### Option B: Using API
```powershell
# Get the route
$route = oc get route rag-backend -n llm-on-techzone -o jsonpath='{.spec.host}'

# Trigger bulk ingestion
curl -X POST "https://$route/api/start-bulk-ingestion"

# Monitor status
curl "https://$route/api/bulk-ingestion-status"
```

## Step 6: Verify Smart Chunking Works

```powershell
# Watch logs for chunk distribution
oc logs -f deployment/rag-backend -n llm-on-techzone | Select-String "Chunk distribution"
```

Expected output:
```
Chunk distribution: {'lifecycle_table': 1, 'feature_code': 250, 'content_section': 25}
```

## Quick Reference

**Check deployment status:**
```powershell
oc get deployment rag-backend -n llm-on-techzone
```

**View recent logs:**
```powershell
oc logs deployment/rag-backend -n llm-on-techzone --tail=100
```

**Follow logs in real-time:**
```powershell
oc logs -f deployment/rag-backend -n llm-on-techzone
```

**Get backend URL:**
```powershell
oc get route rag-backend -n llm-on-techzone -o jsonpath='{.spec.host}'
```

## Success Criteria

- ✅ Build completes successfully
- ✅ Deployment rolls out without errors
- ✅ Logs show "Smart chunking created X chunks"
- ✅ Chunk distribution shows lifecycle_table: 1
- ✅ Lifecycle queries return in <50ms
- ✅ Table structure preserved (Markdown format)

## Made with Bob