# Deploy Enhanced Scraper with Table Preservation

## Overview
This guide walks through deploying the enhanced scraper to IBM Cloud Code Engine and updating the OCP deployment to use the new chunking features.

## What's New in Enhanced Scraper

### 1. Table Preservation
- HTML tables converted to Markdown format
- Preserves structure for Product Lifecycle tables
- Example: `| Type Model | Announced | Available |`

### 2. Metadata Extraction
- Withdrawal dates: "No Longer Available as of December 31, 2024"
- Feature codes: (#EFA1) with attributes
- Location-specific dates (China, South Korea, etc.)

### 3. Enhanced Content Processing
- Tables converted before text extraction
- Prevents duplicate content
- Better structure for LLM comprehension

## Part 1: Deploy to IBM Cloud Code Engine

### Step 1: Navigate to Scraper Directory
```powershell
cd C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual\scraper-test
```

### Step 2: Deploy Using PowerShell Script
```powershell
# Run the deployment script
.\deploy-to-code-engine.ps1

# Or specify parameters
.\deploy-to-code-engine.ps1 -ProjectName "scraper-service" -AppName "ibm-docs-scraper" -Region "eu-gb"
```

### Step 3: Get the Service URL
```powershell
# The script will output the URL, or get it manually:
$SCRAPER_URL = (ibmcloud ce application get --name ibm-docs-scraper --output json | ConvertFrom-Json).status.url
Write-Host "Scraper URL: $SCRAPER_URL"
```

### Step 4: Test the Enhanced Scraper
```powershell
# Test health endpoint
curl "$SCRAPER_URL/health"

# Test E1180 scraping (should show table preservation)
curl "$SCRAPER_URL/scrape-e1180" | ConvertFrom-Json | Select-Object -ExpandProperty stats

# Look for:
# - tables_converted_to_markdown: > 0
# - withdrawal_dates_found: > 0
# - feature_codes_found: > 0
```

## Part 2: Update OCP RAG Backend

### Step 1: Connect to OCP Cluster
```powershell
# Login to your OCP cluster
oc login --token=<your-token> --server=<your-server>

# Switch to your project
oc project <your-project-name>
```

### Step 2: Update Backend Configuration

The RAG backend already has the enhanced web_scraper.py and updated docling_config.py. We just need to ensure it's using the latest code.

#### Option A: Rebuild from Source (Recommended)
```powershell
# Navigate to backend directory
cd C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook\Part3-RAG-Sales-Manual\rag-backend

# Trigger a new build
oc start-build rag-backend --from-dir=. --follow

# Wait for build to complete and pods to restart
oc get pods -w
```

#### Option B: Update Environment Variables Only
If the backend is already deployed with the latest code:
```powershell
# Set the scraper URL (if using external scraper)
oc set env deployment/rag-backend SCRAPER_URL=$SCRAPER_URL

# Verify new chunk size is being used (should be 1024)
oc set env deployment/rag-backend DOCLING_CHUNK_SIZE=1024
oc set env deployment/rag-backend DOCLING_CHUNK_OVERLAP=100

# Restart pods to pick up changes
oc rollout restart deployment/rag-backend
```

### Step 3: Verify Backend Update
```powershell
# Check pod logs
oc logs -f deployment/rag-backend

# Look for:
# - "Docling chunk size: 1024"
# - "Web scraping module loaded successfully"
# - "Table preservation enabled"
```

### Step 4: Test Backend Integration
```powershell
# Get backend URL
$BACKEND_URL = (oc get route rag-backend -o jsonpath='{.spec.host}')

# Test health endpoint
curl "https://$BACKEND_URL/health"

# Test collections endpoint
curl "https://$BACKEND_URL/collections"
```

## Part 3: Update UI (if needed)

The UI (carbon-rag-ui) doesn't need changes - it already calls the backend API which now has enhanced features.

### Verify UI is Working
```powershell
# Get UI URL
$UI_URL = (oc get route carbon-rag-ui -o jsonpath='{.spec.host}')

# Open in browser
Start-Process "https://$UI_URL/sales-manual"
```

## Part 4: Test End-to-End

### Test 1: Scrape a Server with Tables
```powershell
# From the UI, go to Sales Manual page
# Click "Ingest" on E1180 (has Product Lifecycle table)
# Wait for completion
# Check logs for "tables_converted_to_markdown"
```

### Test 2: Query Table Data
```powershell
# In the UI Query tab, ask:
# "When was the IBM Power E1180 announced?"
# 
# Expected: Should return date from Product Lifecycle table
```

### Test 3: Query Withdrawal Dates
```powershell
# Ask: "Is feature code EFA1 still available?"
# 
# Expected: Should find withdrawal date and answer accordingly
```

## Monitoring and Troubleshooting

### Check Scraper Logs (IBM Cloud)
```powershell
ibmcloud ce application logs --name ibm-docs-scraper --follow
```

### Check Backend Logs (OCP)
```powershell
oc logs -f deployment/rag-backend
```

### Check UI Logs (OCP)
```powershell
oc logs -f deployment/carbon-rag-ui
```

### Common Issues

#### Issue: Tables Not Preserved
**Symptom**: Queries about table data return poor results

**Solution**:
```powershell
# Check if tables are being converted
curl "$SCRAPER_URL/scrape-e1180" | ConvertFrom-Json | Select-Object -ExpandProperty stats | Select-Object tables_converted_to_markdown

# Should be > 0
```

#### Issue: Chunk Size Not Updated
**Symptom**: Large tables split across multiple chunks

**Solution**:
```powershell
# Verify environment variable
oc get deployment rag-backend -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="DOCLING_CHUNK_SIZE")].value}'

# Should return: 1024
```

#### Issue: Metadata Not Extracted
**Symptom**: Withdrawal dates not found in queries

**Solution**:
```powershell
# Check scraper output
curl "$SCRAPER_URL/scrape-e1180" | ConvertFrom-Json | Select-Object -ExpandProperty metadata

# Should show withdrawal_dates and feature_codes arrays
```

## Rollback Plan

### Rollback Scraper (IBM Cloud)
```powershell
# Get previous revision
ibmcloud ce application get --name ibm-docs-scraper

# Rollback to previous version
ibmcloud ce application update --name ibm-docs-scraper --image <previous-image>
```

### Rollback Backend (OCP)
```powershell
# Rollback to previous deployment
oc rollout undo deployment/rag-backend

# Or rollback to specific revision
oc rollout undo deployment/rag-backend --to-revision=<revision-number>
```

## Performance Expectations

### Scraper Performance
- **Table Conversion**: +50-100ms per table
- **Metadata Extraction**: +20-50ms per page
- **Overall Impact**: <10% slower, but much better quality

### Backend Performance
- **Larger Chunks**: 1024 vs 768 tokens
- **Storage Impact**: ~30% more storage per document
- **Query Performance**: Similar or better (fewer chunks to search)

## Next Steps

1. ✅ Deploy enhanced scraper to IBM Cloud
2. ✅ Update OCP backend with new code
3. ✅ Test table preservation
4. ✅ Test metadata extraction
5. 📊 Monitor query quality improvements
6. 📈 Track user satisfaction with answers

## Cost Impact

### IBM Cloud Code Engine
- No change in cost (same resources)
- Slightly longer execution time per scrape
- Overall: <5% cost increase

### OCP Storage
- Larger chunks = more storage
- Estimate: +30% storage per indexed document
- For 26 servers: ~500MB → ~650MB

## Success Metrics

Track these metrics to measure improvement:
- ✅ Tables preserved in Markdown format
- ✅ Withdrawal dates extracted
- ✅ Feature codes identified
- ✅ Query accuracy for table-based questions
- ✅ User satisfaction with answers

---
**Created**: 2026-05-06  
**Author**: Bob (AI Assistant)  
**Version**: 1.0