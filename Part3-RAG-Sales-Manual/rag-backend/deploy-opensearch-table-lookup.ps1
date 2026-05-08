#!/usr/bin/env pwsh
# Deploy OpenSearch Table Lookup Enhancement
# This script commits and pushes the changes to trigger OpenShift build

Write-Host "=== OpenSearch Table Lookup Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "table_lookup_service.py")) {
    Write-Host "Error: Must run from rag-backend directory" -ForegroundColor Red
    exit 1
}

# Show what files will be committed
Write-Host "Files to be committed:" -ForegroundColor Yellow
git status --short

Write-Host ""
Write-Host "Changes summary:" -ForegroundColor Yellow
Write-Host "  - table_lookup_service.py: Rewritten to query OpenSearch instead of hardcoded data"
Write-Host "  - app.py: Updated to pass OpenSearch client and embeddings to table service"
Write-Host "  - OPENSEARCH_TABLE_LOOKUP.md: Complete documentation of the enhancement"
Write-Host ""

# Confirm
$confirm = Read-Host "Commit and push these changes? (y/n)"
if ($confirm -ne "y") {
    Write-Host "Deployment cancelled" -ForegroundColor Yellow
    exit 0
}

# Git operations
Write-Host ""
Write-Host "Adding files..." -ForegroundColor Cyan
git add table_lookup_service.py
git add app.py
git add OPENSEARCH_TABLE_LOOKUP.md
git add deploy-opensearch-table-lookup.ps1

Write-Host "Committing..." -ForegroundColor Cyan
git commit -m "feat: OpenSearch-based table lookup for lifecycle queries

- Rewrite table_lookup_service.py to query OpenSearch instead of hardcoded dictionary
- Now works for ANY server with sales manual data loaded (not just 4 hardcoded servers)
- Uses hybrid search (text + vector) to find lifecycle information
- Extracts dates and information directly from sales manual chunks
- No LLM generation needed - returns factual data from manuals
- Updated app.py to pass OpenSearch client and embeddings
- Added comprehensive documentation in OPENSEARCH_TABLE_LOOKUP.md

This fixes the issue where lifecycle queries like 'When did we stop supporting the S924?' 
would fail because S924 wasn't in the hardcoded list. Now it queries the actual sales 
manuals in OpenSearch, making it work for all servers."

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Git commit failed" -ForegroundColor Red
    exit 1
}

Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
git push

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Git push failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. OpenShift will automatically detect the Git push"
Write-Host "2. A new build will start (check: oc get builds)"
Write-Host "3. Once build completes, new pod will deploy"
Write-Host "4. Test with: 'When did we stop supporting the S924?'"
Write-Host ""
Write-Host "Monitor build:" -ForegroundColor Cyan
Write-Host "  oc logs -f bc/rag-backend"
Write-Host ""
Write-Host "Check pod status:" -ForegroundColor Cyan
Write-Host "  oc get pods | grep rag-backend"
Write-Host ""
Write-Host "View logs:" -ForegroundColor Cyan
Write-Host "  oc logs -f deployment/rag-backend"
Write-Host ""

# Made with Bob
