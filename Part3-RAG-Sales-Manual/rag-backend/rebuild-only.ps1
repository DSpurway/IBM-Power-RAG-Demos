# Rebuild image and restart pod without changing deployment structure
# This preserves the existing deployment and just updates the code

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "RAG Backend Code Update (No Deployment Changes)" -ForegroundColor Cyan
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

$APP_NAME = "rag-backend"
$IMAGE_NAME = "${APP_NAME}:latest"

Write-Host ""
Write-Host "Step 1: Starting new build from local code..." -ForegroundColor Yellow
oc start-build $APP_NAME --from-dir=. --follow

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Build completed successfully" -ForegroundColor Green

Write-Host ""
Write-Host "Step 2: Restarting deployment to use new image..." -ForegroundColor Yellow
oc rollout restart deployment/$APP_NAME

Write-Host ""
Write-Host "Step 3: Waiting for rollout to complete..." -ForegroundColor Yellow
oc rollout status deployment/$APP_NAME --timeout=5m

Write-Host ""
Write-Host "Step 4: Adding app label to new pod..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
oc label pod -l deployment=$APP_NAME app=$APP_NAME --overwrite
Write-Host "✓ Pod labeled" -ForegroundColor Green

Write-Host ""
Write-Host "Step 5: Verifying service endpoints..." -ForegroundColor Yellow
$jsonPath = "{.subsets[0].addresses[0].ip}"
$endpoints = oc get endpoints $APP_NAME -o jsonpath=$jsonPath 2>$null
if ($endpoints) {
    Write-Host "✓ Service has endpoints: $endpoints" -ForegroundColor Green
} else {
    Write-Host "⚠ Waiting for endpoints..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    $endpoints = oc get endpoints $APP_NAME -o jsonpath=$jsonPath 2>$null
    if ($endpoints) {
        Write-Host "✓ Service now has endpoints: $endpoints" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Code Update Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "New features deployed:" -ForegroundColor Yellow
Write-Host "  ✓ Activation feature query support" -ForegroundColor White
Write-Host "  ✓ Watson #feature_code_query intent mapping" -ForegroundColor White
Write-Host "  ✓ Source URL inclusion in responses" -ForegroundColor White
Write-Host ""
Write-Host "Check logs with:" -ForegroundColor Yellow
$logCommand = "oc logs -f deployment/$APP_NAME"
Write-Host "  $logCommand" -ForegroundColor White
Write-Host ""

# Made with Bob