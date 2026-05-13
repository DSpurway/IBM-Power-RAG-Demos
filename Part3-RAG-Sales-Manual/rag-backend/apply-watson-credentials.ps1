#!/usr/bin/env pwsh
# Apply Watson Assistant credentials to rag-backend deployment
# This script applies environment variables from the watson-assistant-credentials secret

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Applying Watson Assistant Credentials" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$PROJECT = "llm-on-techzone"
$DEPLOYMENT = "rag-backend"
$SECRET = "watson-assistant-credentials"

Write-Host "`nChecking if secret exists..." -ForegroundColor Green
$secretExists = oc get secret $SECRET -n $PROJECT --ignore-not-found=true
if (-not $secretExists) {
    Write-Host "ERROR: Secret '$SECRET' not found in project '$PROJECT'" -ForegroundColor Red
    Write-Host "Please create the secret first with:" -ForegroundColor Yellow
    Write-Host "  oc create secret generic $SECRET --from-literal=api-key=YOUR_KEY --from-literal=url=YOUR_URL --from-literal=assistant-id=YOUR_ID" -ForegroundColor White
    exit 1
}

Write-Host "Secret found: $SECRET" -ForegroundColor Green

Write-Host "`nApplying credentials to deployment..." -ForegroundColor Green
oc patch deployment/$DEPLOYMENT -n $PROJECT --type=json --patch-file=watson-credentials-patch.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==========================================" -ForegroundColor Cyan
    Write-Host "Watson Credentials Applied Successfully!" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "`nThe deployment will automatically roll out with new credentials." -ForegroundColor Green
} else {
    Write-Host "`nERROR: Failed to apply credentials" -ForegroundColor Red
    exit 1
}

# Made with Bob