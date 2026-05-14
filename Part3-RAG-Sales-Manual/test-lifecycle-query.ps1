# Test lifecycle query directly against backend
$backendUrl = "https://rag-backend-llm-on-techzone.apps.p1265.cecc.ihost.com"

# Bypass SSL certificate validation
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

$body = @{
    question = "When did we stop selling the S924?"
    collection_name = "rag_mtm_9009_42a"
    k = 5
} | ConvertTo-Json

Write-Host "Testing lifecycle query..."
Write-Host "URL: $backendUrl/api/search"
Write-Host "Body: $body"
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$backendUrl/api/search" -Method Post -Body $body -ContentType "application/json"
    Write-Host "Response:"
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error: $_"
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Response: $($_.Exception.Response)"
}

# Made with Bob
