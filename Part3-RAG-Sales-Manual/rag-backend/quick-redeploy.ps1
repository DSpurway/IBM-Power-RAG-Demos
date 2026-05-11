#!/usr/bin/env pwsh
# Quick redeploy script for rag-backend

Write-Host "=== Quick Redeploy rag-backend ===" -ForegroundColor Cyan

# Delete the current pod to force recreation with latest code
Write-Host "Deleting current pod..." -ForegroundColor Yellow
oc delete pod -l app=rag-backend

Write-Host ""
Write-Host "Waiting for new pod to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Watch pod status
Write-Host "Pod status:" -ForegroundColor Cyan
oc get pods -l app=rag-backend

Write-Host ""
Write-Host "=== Redeploy Complete ===" -ForegroundColor Green
Write-Host "The pod will pull the latest image from the registry."
Write-Host "Monitor logs with: oc logs -f deployment/rag-backend"

# Made with Bob
