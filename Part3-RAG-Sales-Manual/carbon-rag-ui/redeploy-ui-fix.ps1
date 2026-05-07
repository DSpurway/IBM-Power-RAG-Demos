#!/usr/bin/env pwsh
# Redeploy Carbon RAG UI with bulk ingestion polling fix

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Redeploying Carbon RAG UI with Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get current project
$PROJECT = oc project -q
Write-Host "Current project: $PROJECT" -ForegroundColor Green
Write-Host ""

# Build configuration
$IMAGE_NAME = "carbon-rag-ui"
$BUILD_CONFIG = "carbon-rag-ui"

# Check if BuildConfig exists
Write-Host "Checking for BuildConfig..." -ForegroundColor Yellow
$bcExists = oc get bc $BUILD_CONFIG 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "BuildConfig '$BUILD_CONFIG' not found. Creating it..." -ForegroundColor Yellow
    
    # Create BuildConfig
    oc new-build --name=$BUILD_CONFIG `
        --binary=true `
        --strategy=docker `
        --to=$IMAGE_NAME`:latest
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create BuildConfig" -ForegroundColor Red
        exit 1
    }
    Write-Host "BuildConfig created successfully" -ForegroundColor Green
} else {
    Write-Host "BuildConfig '$BUILD_CONFIG' exists" -ForegroundColor Green
}
Write-Host ""

# Start build from current directory
Write-Host "Starting build from current directory..." -ForegroundColor Yellow
oc start-build $BUILD_CONFIG --from-dir=. --follow --wait

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host ""

# Trigger rollout
Write-Host "Triggering deployment rollout..." -ForegroundColor Yellow
oc rollout restart deployment/carbon-rag-ui

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to restart deployment" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for rollout to complete..." -ForegroundColor Yellow
oc rollout status deployment/carbon-rag-ui --timeout=5m

if ($LASTEXITCODE -ne 0) {
    Write-Host "Rollout failed or timed out" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Get the route
Write-Host "Getting UI route..." -ForegroundColor Yellow
$ROUTE = oc get route carbon-rag-ui -o jsonpath='{.spec.host}' 2>$null
if ($LASTEXITCODE -eq 0 -and $ROUTE) {
    Write-Host "UI URL: https://$ROUTE/sales-manual" -ForegroundColor Cyan
} else {
    Write-Host "Route not found. Check with: oc get route" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Open the UI in your browser" -ForegroundColor White
Write-Host "2. Open DevTools (F12) -> Console tab" -ForegroundColor White
Write-Host "3. Click 'Load All Documents' button" -ForegroundColor White
Write-Host "4. You should see the progress tile immediately" -ForegroundColor White
Write-Host "5. Watch for console logs: [Bulk Ingestion] Status update" -ForegroundColor White
Write-Host ""

# Made with Bob
