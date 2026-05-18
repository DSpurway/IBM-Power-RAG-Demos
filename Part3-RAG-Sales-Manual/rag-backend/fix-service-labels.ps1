# Fix Service Label Mismatch
# This ensures the service selector matches the deployment labels

Write-Host "`n=== Fixing Service Label Mismatch ===" -ForegroundColor Cyan

# Step 1: Check current deployment labels
Write-Host "`nStep 1: Checking deployment labels..." -ForegroundColor Yellow
$DEPLOYMENT_LABELS = oc get deployment rag-backend -o jsonpath='{.spec.template.metadata.labels}' 2>$null

if ([string]::IsNullOrEmpty($DEPLOYMENT_LABELS)) {
    Write-Host "Error: rag-backend deployment not found" -ForegroundColor Red
    exit 1
}

Write-Host "Deployment pod labels: $DEPLOYMENT_LABELS" -ForegroundColor Green

# Step 2: Check current service selector
Write-Host "`nStep 2: Checking service selector..." -ForegroundColor Yellow
$SERVICE_SELECTOR = oc get svc rag-backend -o jsonpath='{.spec.selector}' 2>$null

if ([string]::IsNullOrEmpty($SERVICE_SELECTOR)) {
    Write-Host "Error: rag-backend service not found" -ForegroundColor Red
    exit 1
}

Write-Host "Service selector: $SERVICE_SELECTOR" -ForegroundColor Green

# Step 3: Delete and recreate the service with correct selector
Write-Host "`nStep 3: Recreating service with correct selector..." -ForegroundColor Yellow

# Delete the service
oc delete svc rag-backend

# Wait a moment
Start-Sleep -Seconds 2

# Recreate the service
oc expose deployment rag-backend --port=5000 --target-port=5000

if ($LASTEXITCODE -eq 0) {
    Write-Host "Service recreated successfully" -ForegroundColor Green
} else {
    Write-Host "Error: Failed to recreate service" -ForegroundColor Red
    exit 1
}

# Step 4: Verify the service selector now matches
Write-Host "`nStep 4: Verifying service selector..." -ForegroundColor Yellow
$NEW_SELECTOR = oc get svc rag-backend -o jsonpath='{.spec.selector}'
Write-Host "New service selector: $NEW_SELECTOR" -ForegroundColor Green

# Step 5: Check if route exists, recreate if needed
Write-Host "`nStep 5: Checking route..." -ForegroundColor Yellow
$ROUTE_EXISTS = oc get route rag-backend 2>$null

if ([string]::IsNullOrEmpty($ROUTE_EXISTS)) {
    Write-Host "Creating route..." -ForegroundColor Yellow
    oc expose svc rag-backend
    Write-Host "Route created" -ForegroundColor Green
} else {
    Write-Host "Route already exists" -ForegroundColor Green
}

# Step 6: Verify endpoints
Write-Host "`nStep 6: Verifying service endpoints..." -ForegroundColor Yellow
$ENDPOINTS = oc get endpoints rag-backend -o jsonpath='{.subsets[*].addresses[*].ip}'

if ([string]::IsNullOrEmpty($ENDPOINTS)) {
    Write-Host "Warning: No endpoints found! Service selector may still not match pods." -ForegroundColor Red
    Write-Host "`nDeployment labels:" -ForegroundColor Yellow
    oc get deployment rag-backend -o jsonpath='{.spec.template.metadata.labels}' | ConvertFrom-Json | ConvertTo-Json
    Write-Host "`nService selector:" -ForegroundColor Yellow
    oc get svc rag-backend -o jsonpath='{.spec.selector}' | ConvertFrom-Json | ConvertTo-Json
} else {
    Write-Host "Endpoints found: $ENDPOINTS" -ForegroundColor Green
}

# Step 7: Test the backend
Write-Host "`nStep 7: Testing backend connectivity..." -ForegroundColor Yellow
$ROUTE = oc get route rag-backend -o jsonpath='{.spec.host}'
Write-Host "Backend URL: https://$ROUTE" -ForegroundColor Cyan

Write-Host "`nTesting health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://$ROUTE/health" -Method GET -UseBasicParsing -TimeoutSec 10
    Write-Host "Health check: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Fix Complete ===" -ForegroundColor Cyan
Write-Host "`nIf still getting 500 errors, check:" -ForegroundColor Yellow
Write-Host "  1. UI backend URL configuration" -ForegroundColor White
Write-Host "  2. CORS settings" -ForegroundColor White
Write-Host "  3. Run: oc get pods -l app=rag-backend" -ForegroundColor White

# Made with Bob
