# Test collections endpoint and show response
Write-Host "Testing /api/collections endpoint..." -ForegroundColor Cyan

$backendUrl = "http://rag-backend:8080"

# Port forward to access backend directly
Write-Host "Setting up port forward..." -ForegroundColor Yellow
$portForward = Start-Process -FilePath "oc" -ArgumentList "port-forward svc/rag-backend 8080:8080" -PassThru -NoNewWindow

Start-Sleep -Seconds 3

try {
    Write-Host "Calling /api/collections..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/collections" -Method GET
    
    Write-Host "`nResponse:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
    
    Write-Host "`nCollections Map:" -ForegroundColor Cyan
    $response.collections_map | ConvertTo-Json -Depth 5
    
    Write-Host "`nCollections Details:" -ForegroundColor Cyan
    $response.collections_details | ConvertTo-Json -Depth 5
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
} finally {
    Write-Host "`nStopping port forward..." -ForegroundColor Yellow
    Stop-Process -Id $portForward.Id -Force
}

# Made with Bob
