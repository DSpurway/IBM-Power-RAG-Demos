# Deploy Smart Chunking to Remote OCP Cluster
# This script commits changes to GitHub and triggers OCP rebuild

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Smart Chunking Deployment Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$NAMESPACE = "llm-on-techzone"
$DEPLOYMENT = "rag-backend"
$GITHUB_BRANCH = "main"

# Step 1: Check current git status
Write-Host "Step 1: Checking git status..." -ForegroundColor Yellow
git status

Write-Host ""
$continue = Read-Host "Do you want to commit and push these changes? (y/n)"
if ($continue -ne "y") {
    Write-Host "Deployment cancelled." -ForegroundColor Red
    exit 1
}

# Step 2: Commit changes to git
Write-Host ""
Write-Host "Step 2: Committing changes to git..." -ForegroundColor Yellow
git add sales_manual_chunker.py
git add app.py
git add SMART_CHUNKING_DEPLOYMENT.md
git add deploy-smart-chunking.ps1

$commitMessage = "feat: Add smart hierarchical chunking for Sales Manuals

- Add sales_manual_chunker.py with intelligent chunking
- Preserve lifecycle tables as Markdown for direct lookup
- Extract feature codes with metadata (withdrawal dates, CSU, etc.)
- Create semantic chunks for better RAG retrieval
- Update /ingest-scraped-content endpoint to use new chunker
- Add deployment guide

This enables hybrid query system:
- Direct table lookup (no LLM) for lifecycle dates
- Metadata search for feature codes
- Full RAG for complex queries

Expected: ~220-320 chunks per server vs 1 massive 5MB chunk"

git commit -m "$commitMessage"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Git commit failed!" -ForegroundColor Red
    exit 1
}

# Step 3: Push to GitHub
Write-Host ""
Write-Host "Step 3: Pushing to GitHub..." -ForegroundColor Yellow
git push origin $GITHUB_BRANCH

if ($LASTEXITCODE -ne 0) {
    Write-Host "Git push failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Changes pushed to GitHub" -ForegroundColor Green

# Step 4: Trigger OCP rebuild
Write-Host ""
Write-Host "Step 4: Triggering OCP rebuild..." -ForegroundColor Yellow

# Check if we're logged into OCP
$ocStatus = oc whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged into OCP. Please run: oc login" -ForegroundColor Red
    exit 1
}

Write-Host "Logged in as: $ocStatus" -ForegroundColor Green

# Start new build from GitHub
Write-Host ""
Write-Host "Starting new build from GitHub..." -ForegroundColor Yellow
oc start-build $DEPLOYMENT -n $NAMESPACE --follow

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Build completed successfully" -ForegroundColor Green

# Step 5: Wait for rollout
Write-Host ""
Write-Host "Step 5: Waiting for deployment rollout..." -ForegroundColor Yellow
oc rollout status deployment/$DEPLOYMENT -n $NAMESPACE

if ($LASTEXITCODE -ne 0) {
    Write-Host "Rollout failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Deployment rolled out successfully" -ForegroundColor Green

# Step 6: Verify deployment
Write-Host ""
Write-Host "Step 6: Verifying deployment..." -ForegroundColor Yellow

# Get pod name
$podName = oc get pods -n $NAMESPACE -l app=$DEPLOYMENT -o jsonpath='{.items[0].metadata.name}' 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not find pod!" -ForegroundColor Red
    exit 1
}

Write-Host "Pod: $podName" -ForegroundColor Green

# Check logs for successful startup
Write-Host ""
Write-Host "Checking logs for smart chunker..." -ForegroundColor Yellow
$logs = oc logs $podName -n $NAMESPACE --tail=50 2>&1

if ($logs -match "sales_manual_chunker" -or $logs -match "Smart chunking") {
    Write-Host "✓ Smart chunker module loaded successfully" -ForegroundColor Green
} else {
    Write-Host "⚠ Could not verify smart chunker in logs" -ForegroundColor Yellow
    Write-Host "Recent logs:" -ForegroundColor Gray
    Write-Host $logs -ForegroundColor Gray
}

# Step 7: Test health endpoint
Write-Host ""
Write-Host "Step 7: Testing health endpoint..." -ForegroundColor Yellow

$route = oc get route $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.spec.host}' 2>&1
if ($LASTEXITCODE -eq 0) {
    $healthUrl = "https://$route/health"
    Write-Host "Health URL: $healthUrl" -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10
        Write-Host "✓ Health check passed" -ForegroundColor Green
        Write-Host "Status: $($response.status)" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Health check failed: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠ Could not get route" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ Changes committed to GitHub" -ForegroundColor Green
Write-Host "✓ OCP build completed" -ForegroundColor Green
Write-Host "✓ Deployment rolled out" -ForegroundColor Green
Write-Host "✓ Pod is running" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Re-ingest all servers using UI or API" -ForegroundColor White
Write-Host "2. Test lifecycle query: 'When did we stop selling S924?'" -ForegroundColor White
Write-Host "3. Monitor chunk distribution in logs" -ForegroundColor White
Write-Host ""
Write-Host "To re-ingest all servers:" -ForegroundColor Yellow
Write-Host "  curl -X POST https://$route/api/start-bulk-ingestion" -ForegroundColor Cyan
Write-Host ""
Write-Host "To monitor ingestion:" -ForegroundColor Yellow
Write-Host "  oc logs -f deployment/$DEPLOYMENT -n $NAMESPACE | Select-String 'Chunk distribution'" -ForegroundColor Cyan
Write-Host ""
Write-Host "Deployment complete! 🎉" -ForegroundColor Green

# Made with Bob
