# Fix Deployment Selector Issue
# This script deletes and recreates the rag-backend deployment
# Includes Watson Assistant credentials and proper labels

Write-Host "`n=== Fixing RAG Backend Deployment ===" -ForegroundColor Cyan

# Step 1: Check if Watson Assistant secret exists
Write-Host "`nStep 1: Checking Watson Assistant credentials..." -ForegroundColor Yellow
$SECRET_EXISTS = oc get secret watson-assistant-credentials 2>$null
if ([string]::IsNullOrEmpty($SECRET_EXISTS)) {
    Write-Host "Warning: watson-assistant-credentials secret not found" -ForegroundColor Yellow
    Write-Host "Watson Assistant integration will not be available" -ForegroundColor Yellow
    $HAS_WATSON = $false
} else {
    Write-Host "Watson Assistant credentials found" -ForegroundColor Green
    $HAS_WATSON = $true
}

# Step 2: Delete the existing deployment
Write-Host "`nStep 2: Deleting existing deployment..." -ForegroundColor Yellow
oc delete deployment rag-backend

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Deployment deletion failed or deployment doesn't exist" -ForegroundColor Yellow
}

# Wait a moment for cleanup
Start-Sleep -Seconds 3

# Step 3: Recreate the deployment using the build
Write-Host "`nStep 3: Creating new deployment from latest build..." -ForegroundColor Yellow

# Get the latest image
$IMAGE = oc get imagestream rag-backend -o jsonpath='{.status.tags[0].items[0].dockerImageReference}'

if ([string]::IsNullOrEmpty($IMAGE)) {
    Write-Host "Error: Could not find rag-backend image" -ForegroundColor Red
    exit 1
}

Write-Host "Using image: $IMAGE" -ForegroundColor Green

# Create new deployment with proper labels
oc create deployment rag-backend --image=$IMAGE

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to create deployment" -ForegroundColor Red
    exit 1
}

# Step 4: Add proper labels to deployment
Write-Host "`nStep 4: Adding labels to deployment..." -ForegroundColor Yellow
oc label deployment/rag-backend app=rag-backend --overwrite
oc label deployment/rag-backend component=backend --overwrite

# Step 5: Configure the deployment
Write-Host "`nStep 5: Configuring environment variables..." -ForegroundColor Yellow

# Set basic environment variables
oc set env deployment/rag-backend `
    OPENSEARCH_HOST=opensearch-service `
    OPENSEARCH_PORT=9200 `
    OPENSEARCH_USERNAME=admin `
    OPENSEARCH_PASSWORD=admin `
    GRANITE_HOST=granite-llama-service `
    GRANITE_PORT=8080 `
    TINYLLAMA_HOST=tinyllama-service `
    TINYLLAMA_PORT=8080

# Add Watson Assistant credentials if secret exists
if ($HAS_WATSON) {
    Write-Host "Adding Watson Assistant credentials from secret..." -ForegroundColor Yellow
    oc set env deployment/rag-backend --from=secret/watson-assistant-credentials
    Write-Host "Watson Assistant credentials configured" -ForegroundColor Green
}

# Step 6: Ensure service exists with proper labels
Write-Host "`nStep 6: Ensuring service exists..." -ForegroundColor Yellow
$SERVICE_EXISTS = oc get svc rag-backend 2>$null
if ([string]::IsNullOrEmpty($SERVICE_EXISTS)) {
    oc expose deployment rag-backend --port=5000
    oc label svc/rag-backend app=rag-backend --overwrite
    oc label svc/rag-backend component=backend --overwrite
    Write-Host "Service created with labels" -ForegroundColor Green
} else {
    # Ensure service has proper labels
    oc label svc/rag-backend app=rag-backend --overwrite
    oc label svc/rag-backend component=backend --overwrite
    Write-Host "Service already exists, labels updated" -ForegroundColor Green
}

# Step 7: Ensure route exists
Write-Host "`nStep 7: Ensuring route exists..." -ForegroundColor Yellow
$ROUTE_EXISTS = oc get route rag-backend 2>$null
if ([string]::IsNullOrEmpty($ROUTE_EXISTS)) {
    oc expose svc rag-backend
    Write-Host "Route created" -ForegroundColor Green
} else {
    Write-Host "Route already exists" -ForegroundColor Green
}

# Step 8: Wait for deployment to be ready
Write-Host "`nStep 8: Waiting for deployment to be ready..." -ForegroundColor Yellow
oc rollout status deployment/rag-backend --timeout=5m

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Deployment fixed successfully!" -ForegroundColor Green
    
    # Show the route
    $ROUTE = oc get route rag-backend -o jsonpath='{.spec.host}'
    Write-Host "`nBackend URL: https://$ROUTE" -ForegroundColor Cyan
    
    # Show pod status
    Write-Host "`nPod Status:" -ForegroundColor Yellow
    oc get pods -l app=rag-backend
    
    # Show configuration summary
    Write-Host "`nConfiguration Summary:" -ForegroundColor Yellow
    Write-Host "  - Granite LLM: granite-llama-service:8080" -ForegroundColor White
    Write-Host "  - OpenSearch: opensearch-service:9200" -ForegroundColor White
    if ($HAS_WATSON) {
        Write-Host "  - Watson Assistant: Configured from secret" -ForegroundColor White
    } else {
        Write-Host "  - Watson Assistant: Not configured" -ForegroundColor Gray
    }
    
    Write-Host "`nTest the activation feature enhancement:" -ForegroundColor Yellow
    Write-Host "  Ask: 'What processor activations are available for the E1080?'" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Deployment failed!" -ForegroundColor Red
    Write-Host "`nCheck logs with: oc logs -f deployment/rag-backend" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=== Fix Complete ===" -ForegroundColor Cyan

# Made with Bob
