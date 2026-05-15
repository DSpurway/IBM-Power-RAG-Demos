# Test S922 (9009-22A) Ingestion with Improved Chunking
$ErrorActionPreference = "Stop"

# Skip certificate validation for self-signed certs (Windows PowerShell 5.1)
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
Write-Host "Testing S922 (9009-22A) Ingestion" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Get backend route
$BACKEND_URL = "https://$(oc get route rag-backend -o jsonpath='{.spec.host}')"
Write-Host "Backend URL: $BACKEND_URL" -ForegroundColor Green

# S922 details
$SERVER_MODEL = "S922"
$MTM = "9009-22A"
$URL = "https://www.ibm.com/docs/en/announcements/power-system-s922-9009-22a"

Write-Host ""
Write-Host "Server: $SERVER_MODEL" -ForegroundColor Yellow
Write-Host "MTM: $MTM" -ForegroundColor Yellow
Write-Host "URL: $URL" -ForegroundColor Yellow

# Create request body
$body = @{
    mtm = $MTM
    server_model = $SERVER_MODEL
    url = $URL
} | ConvertTo-Json

Write-Host ""
Write-Host "Step 1: Triggering ingestion..." -ForegroundColor Yellow

$response = Invoke-RestMethod -Uri "$BACKEND_URL/api/rag/ingest-sales-manual" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

Write-Host "Response:" -ForegroundColor Green
$response | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "Step 2: Waiting 15 seconds for processing..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "Step 3: Querying for lifecycle dates..." -ForegroundColor Yellow

# Query for lifecycle dates to see chunk size
$query = @{
    query = "When was the S922 announced?"
    collection = "sales_manuals"
} | ConvertTo-Json

$queryResponse = Invoke-RestMethod -Uri "$BACKEND_URL/api/rag/query" `
    -Method Post `
    -ContentType "application/json" `
    -Body $query

Write-Host "Query Response:" -ForegroundColor Green
$queryResponse | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

# Made with Bob
