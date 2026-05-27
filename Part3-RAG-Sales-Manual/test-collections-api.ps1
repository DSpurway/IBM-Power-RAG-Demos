# Quick test of collections API
$BACKEND_URL = "https://rag-backend-llm-on-techzone.apps.p1265.cecc.ihost.com"

Write-Host "Testing collections API..." -ForegroundColor Yellow
Write-Host "URL: $BACKEND_URL/api/collections" -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$BACKEND_URL/api/collections" -Method Get -TimeoutSec 10
    
    Write-Host "✓ API Response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
    
    Write-Host ""
    Write-Host "Collections found:" -ForegroundColor Cyan
    if ($response.collections) {
        $response.collections | ForEach-Object {
            Write-Host "  - $($_.name) ($($_.document_count) docs)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  (No collections)" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "✗ API call failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

# Made with Bob
