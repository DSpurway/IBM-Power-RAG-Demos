# Test Backend Health and Collections Endpoint

$ErrorActionPreference = "Stop"

# Skip certificate validation
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

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Backend Health Check" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Get backend route
$BACKEND_URL = "https://$(oc get route rag-backend -o jsonpath='{.spec.host}')"
Write-Host "Backend URL: $BACKEND_URL" -ForegroundColor Green

Write-Host ""
Write-Host "Test 1: Health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BACKEND_URL/health" -Method Get
    Write-Host "✓ Health check passed" -ForegroundColor Green
    $health | ConvertTo-Json
} catch {
    Write-Host "✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 2: Collections endpoint..." -ForegroundColor Yellow
try {
    $collections = Invoke-RestMethod -Uri "$BACKEND_URL/api/collections" -Method Get
    Write-Host "✓ Collections endpoint working" -ForegroundColor Green
    $collections | ConvertTo-Json -Depth 5
} catch {
    Write-Host "✗ Collections endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan

# Made with Bob
