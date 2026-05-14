# Cleanup old rag-backend-opensearch resources and redeploy with correct name
# This script removes the incorrectly named resources and deploys fresh with "rag-backend"

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Cleanup and Redeploy RAG Backend" -ForegroundColor Cyan
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

Write-Host "`n=========================================="
Write-Host "Step 1: Cleaning up old resources..." -ForegroundColor Yellow
Write-Host "==========================================" 

# Delete old resources with wrong name
$oldResources = @(
    "buildconfig/rag-backend-opensearch",
    "imagestream/rag-backend-opensearch",
    "deployment/rag-backend-opensearch",
    "service/rag-backend-opensearch",
    "route/rag-backend-opensearch"
)

foreach ($resource in $oldResources) {
    Write-Host "Checking for $resource..." -ForegroundColor Gray
    $exists = oc get $resource 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Deleting $resource" -ForegroundColor Yellow
        oc delete $resource --ignore-not-found=true
    } else {
        Write-Host "  Not found (OK)" -ForegroundColor Gray
    }
}

Write-Host "`n=========================================="
Write-Host "Step 2: Deploying with correct name..." -ForegroundColor Yellow
Write-Host "==========================================" 

# Run the corrected deployment script
Write-Host "`nRunning deploy.ps1..." -ForegroundColor Green
& "$PSScriptRoot\deploy.ps1"

Write-Host "`n=========================================="
Write-Host "Cleanup and Redeploy Complete!" -ForegroundColor Green
Write-Host "==========================================" 
Write-Host "`nNew resources created with name: rag-backend" -ForegroundColor Cyan
Write-Host "`nTo check status:" -ForegroundColor Yellow
Write-Host "  oc get all -l app=rag-backend" -ForegroundColor White
Write-Host "`nTo view logs:" -ForegroundColor Yellow
Write-Host "  oc logs -f deployment/rag-backend" -ForegroundColor White
Write-Host "`nTo get route URL:" -ForegroundColor Yellow
Write-Host "  oc get route rag-backend" -ForegroundColor White

# Made with Bob
