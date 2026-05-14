# Safe redeployment script that preserves secrets and fixes label issues
# This script deletes and recreates the deployment with correct labels

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "RAG Backend Safe Redeployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if logged into OpenShift
try {
    $null = oc whoami 2>&1
} catch {
    Write-Host "Error: Not logged into OpenShift. Please run 'oc login' first." -ForegroundColor Red
    exit 1
}

$PROJECT = oc project -q
Write-Host "Working in project: $PROJECT" -ForegroundColor Green

# Configuration
$APP_NAME = "rag-backend"

Write-Host ""
Write-Host "Step 1: Checking for Watson Assistant secret..." -ForegroundColor Yellow
$secretExists = oc get secret watson-assistant-credentials --ignore-not-found=true
if ($secretExists) {
    Write-Host "✓ Watson Assistant secret exists and will be preserved" -ForegroundColor Green
} else {
    Write-Host "⚠ Watson Assistant secret not found - you'll need to recreate it" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 2: Deleting existing deployment (preserving service and route)..." -ForegroundColor Yellow
oc delete deployment $APP_NAME --ignore-not-found=true
Write-Host "✓ Deployment deleted" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Applying deployment YAML with correct labels..." -ForegroundColor Yellow
oc apply -f rag-backend-deploy.yaml
Write-Host "✓ Deployment created with correct labels" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Waiting for deployment to be ready..." -ForegroundColor Yellow
oc rollout status deployment/$APP_NAME --timeout=5m

Write-Host ""
Write-Host "Step 5: Verifying pod labels..." -ForegroundColor Yellow
$podLabels = oc get pods -l deployment=$APP_NAME -o jsonpath='{.items[0].metadata.labels}' 2>$null
if ($podLabels) {
    Write-Host "Pod labels: $podLabels" -ForegroundColor White
    if ($podLabels -match '"app":"rag-backend"' -and $podLabels -match '"deployment":"rag-backend"') {
        Write-Host "✓ Pod has both required labels" -ForegroundColor Green
    } else {
        Write-Host "⚠ Pod labels may be incomplete" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Step 6: Verifying service endpoints..." -ForegroundColor Yellow
$endpoints = oc get endpoints $APP_NAME -o jsonpath='{.subsets[0].addresses[0].ip}' 2>$null
if ($endpoints) {
    Write-Host "✓ Service has endpoints: $endpoints" -ForegroundColor Green
} else {
    Write-Host "⚠ Service has no endpoints yet - waiting..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    $endpoints = oc get endpoints $APP_NAME -o jsonpath='{.subsets[0].addresses[0].ip}' 2>$null
    if ($endpoints) {
        Write-Host "✓ Service now has endpoints: $endpoints" -ForegroundColor Green
    } else {
        Write-Host "✗ Service still has no endpoints - check pod status" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Redeployment Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Getting route URL..." -ForegroundColor Yellow
$ROUTE_URL = oc get route $APP_NAME -o jsonpath='{.spec.host}'
Write-Host ""
Write-Host "RAG Backend URL: https://$ROUTE_URL" -ForegroundColor Green
Write-Host ""
Write-Host "Check logs with:" -ForegroundColor Yellow
Write-Host "  oc logs -f deployment/$APP_NAME" -ForegroundColor White
Write-Host ""

# Made with Bob