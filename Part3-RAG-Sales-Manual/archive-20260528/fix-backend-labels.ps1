# Fix Backend Pod Labels
# After rebuild, pods may be missing the app=rag-backend label

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Fixing Backend Pod Labels" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Step 1: Checking current pod labels..." -ForegroundColor Yellow
oc get pods -l deployment=rag-backend -o custom-columns=NAME:.metadata.name,LABELS:.metadata.labels

Write-Host ""
Write-Host "Step 2: Adding app=rag-backend label to pods..." -ForegroundColor Yellow
oc label pod -l deployment=rag-backend app=rag-backend --overwrite

Write-Host ""
Write-Host "Step 3: Verifying labels..." -ForegroundColor Yellow
oc get pods -l app=rag-backend -o custom-columns=NAME:.metadata.name,LABELS:.metadata.labels

Write-Host ""
Write-Host "Step 4: Checking service endpoints..." -ForegroundColor Yellow
oc get endpoints rag-backend

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✓ Labels Fixed!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "The service should now be able to route to the backend pods." -ForegroundColor Green
Write-Host "Refresh the UI to verify collections load correctly." -ForegroundColor Yellow

# Made with Bob
