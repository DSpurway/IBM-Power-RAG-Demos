# Granite Service Deployment Script for OpenShift (PowerShell)
# This deploys the Granite 4.0 Micro model for complex RAG queries

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Granite Service Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Get the current project
$PROJECT = oc project -q
Write-Host "Current project: $PROJECT" -ForegroundColor Green
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "Dockerfile")) {
    Write-Host "Error: Dockerfile not found. Please run this script from the granite-service directory." -ForegroundColor Red
    exit 1
}

# Build the container image
Write-Host "Step 1: Building Granite service container image..." -ForegroundColor Yellow
Write-Host "This will take several minutes as it downloads the Granite 4.0 Micro model (~2.5GB)" -ForegroundColor Yellow
try {
    oc new-build --name=granite-service --binary --strategy=docker 2>$null
} catch {
    Write-Host "Build config already exists" -ForegroundColor Gray
}
oc start-build granite-service --from-dir=. --follow --wait

Write-Host ""
Write-Host "Step 2: Deploying Granite service..." -ForegroundColor Yellow
oc apply -f granite-deploy.yaml

Write-Host ""
Write-Host "Step 3: Creating service..." -ForegroundColor Yellow
oc apply -f granite-svc.yaml

Write-Host ""
Write-Host "Step 4: Creating route..." -ForegroundColor Yellow
oc apply -f granite-route.yaml

Write-Host ""
Write-Host "Step 5: Waiting for deployment to be ready..." -ForegroundColor Yellow
oc rollout status deployment/granite-service --timeout=10m

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Get the route URL
$ROUTE_URL = oc get route granite-service -o jsonpath='{.spec.host}'
Write-Host "Granite service is available at: https://$ROUTE_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test the service with:" -ForegroundColor Yellow
Write-Host "  curl https://$ROUTE_URL/health" -ForegroundColor White
Write-Host ""
Write-Host "The RAG backend will automatically use this service for complex queries." -ForegroundColor Green
Write-Host "Make sure to set GRANITE_HOST=granite-service in the rag-backend deployment." -ForegroundColor Green
Write-Host ""

# Made with Bob
