# Quick deployment script to fix the server status display issue
# This deploys both backend and frontend with the updated status checking logic

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deploying Status Display Fix" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if logged into OpenShift
try {
    $null = oc whoami 2>&1
} catch {
    Write-Host "Error: Not logged into OpenShift. Please run 'oc login' first." -ForegroundColor Red
    exit 1
}

$PROJECT = oc project -q
Write-Host "Deploying to project: $PROJECT" -ForegroundColor Green
Write-Host ""

# Step 1: Deploy Backend
Write-Host "Step 1: Deploying RAG Backend with status fix..." -ForegroundColor Yellow
Set-Location -Path "Part3-RAG-Sales-Manual/rag-backend"

Write-Host "  - Starting backend build..." -ForegroundColor Cyan
oc start-build rag-backend-opensearch --from-dir=. --follow

if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "  - Waiting for backend rollout..." -ForegroundColor Cyan
oc rollout status deployment/rag-backend-opensearch --timeout=5m

Write-Host "  - Backend deployed successfully!" -ForegroundColor Green
Write-Host ""

# Step 2: Deploy Frontend
Write-Host "Step 2: Deploying Carbon UI with status fix..." -ForegroundColor Yellow
Set-Location -Path "../carbon-rag-ui"

Write-Host "  - Starting frontend build..." -ForegroundColor Cyan
oc start-build carbon-rag-ui --from-dir=. --follow

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "  - Waiting for frontend rollout..." -ForegroundColor Cyan
oc rollout status deployment/carbon-rag-ui --timeout=5m

Write-Host "  - Frontend deployed successfully!" -ForegroundColor Green
Write-Host ""

# Get URLs
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$BACKEND_URL = oc get route rag-backend-opensearch -o jsonpath='{.spec.host}' 2>$null
$FRONTEND_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}' 2>$null

if ($BACKEND_URL) {
    Write-Host "Backend URL:  https://$BACKEND_URL" -ForegroundColor Green
    Write-Host "Test backend: curl https://$BACKEND_URL/api/collections" -ForegroundColor White
}

if ($FRONTEND_URL) {
    Write-Host "Frontend URL: https://$FRONTEND_URL" -ForegroundColor Green
    Write-Host "Open in browser to see the fixed status display!" -ForegroundColor White
}

Write-Host ""
Write-Host "Changes deployed:" -ForegroundColor Yellow
Write-Host "  ✓ Backend now returns document counts for each indexed server" -ForegroundColor White
Write-Host "  ✓ Frontend displays actual document counts in the 'Docs' column" -ForegroundColor White
Write-Host "  ✓ Status messages show total document count" -ForegroundColor White
Write-Host ""
Write-Host "The UI should now correctly show which servers are indexed!" -ForegroundColor Green
Write-Host ""

# Return to original directory
Set-Location -Path "../.."

# Made with Bob