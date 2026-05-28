# Test collections endpoint through UI
Write-Host "Testing /api/rag/collections through UI..." -ForegroundColor Cyan

$uiUrl = "https://carbon-rag-ui-llm-on-techzone.apps.p1265.cecc.ihost.com"

try {
    Write-Host "Calling $uiUrl/api/rag/collections..." -ForegroundColor Yellow
    
    # Disable SSL verification for self-signed certs
    add-type @"
        using System.Net;
        using System.Security.Cryptography.X509Certificates;
        public class TrustAllCertsPolicy : ICertificatePolicy {
            public bool CheckValidationResult(
                ServicePoint srvPoint, X509Certificate certificate,
                WebRequest request, int certificateProblem) {
                return true;
            }
        }
"@
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    
    $response = Invoke-RestMethod -Uri "$uiUrl/api/rag/collections" -Method GET
    
    Write-Host "`nFull Response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
    
    Write-Host "`nCollections Map Keys:" -ForegroundColor Cyan
    if ($response.collections_map) {
        $response.collections_map.PSObject.Properties | ForEach-Object { Write-Host "  $($_.Name): $($_.Value)" }
    } else {
        Write-Host "  (empty or null)" -ForegroundColor Red
    }
    
    Write-Host "`nCollections Details Keys:" -ForegroundColor Cyan
    if ($response.collections_details) {
        $response.collections_details.PSObject.Properties | ForEach-Object { 
            Write-Host "  $($_.Name): $($_.Value.document_count) docs" 
        }
    } else {
        Write-Host "  (empty or null)" -ForegroundColor Red
    }
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

# Made with Bob
