# Test S922 (9009-22A) Ingestion - Direct Method
# Uses backend's built-in web scraper instead of external scraper service

$ErrorActionPreference = "Stop"

# Skip certificate validation for self-signed certs
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
Write-Host "Testing S922 Direct Ingestion" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Get backend route
$BACKEND_URL = "https://$(oc get route rag-backend -o jsonpath='{.spec.host}')"
Write-Host "Backend URL: $BACKEND_URL" -ForegroundColor Green

# S922 details
$URL = "https://www.ibm.com/docs/en/announcements/power-system-s922-9009-22a"

Write-Host ""
Write-Host "URL: $URL" -ForegroundColor Yellow
Write-Host ""
Write-Host "Step 1: Scraping content locally..." -ForegroundColor Yellow

# Use Python to scrape with the backend's web_scraper module
$pythonScript = @"
import sys
sys.path.insert(0, 'Part3-RAG-Sales-Manual/rag-backend')
from web_scraper import IBMDocsScraper
import json

url = '$URL'
scraper = IBMDocsScraper()
result = scraper.scrape_page(url)

if result['success']:
    # Add metadata for ingestion
    result['mtm'] = '9009-22A'
    result['server_model'] = 'S922'
    print(json.dumps(result))
else:
    print(json.dumps({'error': result.get('error', 'Scraping failed')}), file=sys.stderr)
    sys.exit(1)
"@

try {
    $scrapedData = python -c $pythonScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Scraping failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Scraping successful" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Step 2: Sending to backend for ingestion..." -ForegroundColor Yellow
    
    $response = Invoke-RestMethod -Uri "$BACKEND_URL/ingest-scraped-content" `
        -Method Post `
        -ContentType "application/json" `
        -Body $scrapedData
    
    Write-Host "Response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
    
    Write-Host ""
    Write-Host "Step 3: Waiting 10 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Write-Host ""
    Write-Host "Step 4: Testing lifecycle query..." -ForegroundColor Yellow
    
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
    
} catch {
    Write-Host ""
    Write-Host "Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
    exit 1
}

# Made with Bob
