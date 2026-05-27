# Test E980 Ingestion - Complete End-to-End Test
# Uses scraped content from Code Engine scraper service

$ErrorActionPreference = "Stop"

Write-Host "=== E980 Sales Manual Ingestion Test ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$BACKEND_URL = "https://rag-backend-llm-on-techzone.apps.p1265.cecc.ihost.com"
$E980_URL = "https://www.ibm.com/docs/en/announcements/archive/ENUS918-143?region=US"
$E980_MTM = "9080-M9S"
$E980_NAME = "IBM Power System E980"

# Step 1: Get scraper URL
Write-Host "Step 1: Getting scraper service URL..." -ForegroundColor Yellow
$scraperUrlFile = "scraper-url.txt"

if (Test-Path $scraperUrlFile) {
    $SCRAPER_URL = Get-Content $scraperUrlFile -Raw
    $SCRAPER_URL = $SCRAPER_URL.Trim()
    Write-Host "✓ Using cached scraper URL: $SCRAPER_URL" -ForegroundColor Green
} else {
    Write-Host "✗ Scraper URL not found. Run get-scraper-url-simple.sh first" -ForegroundColor Red
    exit 1
}

# Step 2: Scrape E980 content
Write-Host ""
Write-Host "Step 2: Scraping E980 Sales Manual..." -ForegroundColor Yellow
Write-Host "URL: $E980_URL" -ForegroundColor Gray

$encodedUrl = [System.Web.HttpUtility]::UrlEncode($E980_URL)
$scrapeUrl = "$SCRAPER_URL/scrape?url=$encodedUrl"

Write-Host "Calling scraper (this may take 15-20 seconds)..." -ForegroundColor Gray

try {
    $scrapeResponse = Invoke-RestMethod -Uri $scrapeUrl -Method Get -TimeoutSec 60
    
    if ($scrapeResponse.success) {
        $contentLength = $scrapeResponse.full_text.Length
        $featureCount = ($scrapeResponse.full_text -split '#[A-Z0-9]{4}').Count - 1
        
        Write-Host "✓ Scraping successful!" -ForegroundColor Green
        Write-Host "  Content length: $contentLength characters" -ForegroundColor Gray
        Write-Host "  Feature codes found: $featureCount" -ForegroundColor Gray
        Write-Host "  Page title: $($scrapeResponse.page_title)" -ForegroundColor Gray
        
        # Save scraped content for inspection
        $scrapeResponse | ConvertTo-Json -Depth 10 | Out-File "e980-scraped-content.json" -Encoding UTF8
        Write-Host "  Saved to: e980-scraped-content.json" -ForegroundColor Gray
    } else {
        Write-Host "✗ Scraping failed: $($scrapeResponse.error)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Scraper request failed: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Ingest into backend
Write-Host ""
Write-Host "Step 3: Ingesting into RAG backend..." -ForegroundColor Yellow
Write-Host "Backend: $BACKEND_URL" -ForegroundColor Gray
Write-Host "Collection: rag_mtm_9080_m9s" -ForegroundColor Gray

# Prepare ingestion payload
$ingestPayload = @{
    success = $true
    url = $E980_URL
    page_title = $E980_NAME
    full_text = $scrapeResponse.full_text
    server_model = "E980"
    mtm = $E980_MTM
    content_length = $scrapeResponse.full_text.Length
    feature_codes_count = $featureCount
} | ConvertTo-Json -Depth 10

try {
    $ingestResponse = Invoke-RestMethod `
        -Uri "$BACKEND_URL/ingest-scraped-content" `
        -Method Post `
        -ContentType "application/json" `
        -Body $ingestPayload `
        -TimeoutSec 120
    
    Write-Host "✓ Ingestion successful!" -ForegroundColor Green
    Write-Host "  Chunks created: $($ingestResponse.chunks_created)" -ForegroundColor Gray
    Write-Host "  Chunks indexed: $($ingestResponse.chunks_indexed)" -ForegroundColor Gray
    Write-Host "  Collection: $($ingestResponse.collection_name)" -ForegroundColor Gray
    
    # Display chunk distribution
    if ($ingestResponse.chunk_distribution) {
        Write-Host ""
        Write-Host "Chunk Distribution:" -ForegroundColor Cyan
        $ingestResponse.chunk_distribution.PSObject.Properties | ForEach-Object {
            Write-Host "  $($_.Name): $($_.Value)" -ForegroundColor Gray
        }
    }
    
    # Save ingestion response
    $ingestResponse | ConvertTo-Json -Depth 10 | Out-File "e980-ingestion-response.json" -Encoding UTF8
    Write-Host ""
    Write-Host "  Saved to: e980-ingestion-response.json" -ForegroundColor Gray
    
} catch {
    Write-Host "✗ Ingestion failed: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# Step 4: Validate ingestion
Write-Host ""
Write-Host "Step 4: Validating ingestion quality..." -ForegroundColor Yellow

# Check for lifecycle table
if ($scrapeResponse.full_text -match "Product life cycle dates") {
    Write-Host "✓ Lifecycle table found in source" -ForegroundColor Green
} else {
    Write-Host "✗ WARNING: No lifecycle table in source" -ForegroundColor Yellow
}

# Check for activation features
$activationMatches = [regex]::Matches($scrapeResponse.full_text, '\(#[A-Z0-9]{4}\)[^\n]*activation', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
if ($activationMatches.Count -gt 0) {
    Write-Host "✓ Found $($activationMatches.Count) activation features" -ForegroundColor Green
} else {
    Write-Host "⚠ No activation features found" -ForegroundColor Yellow
}

# Check for mixed MTM contamination
$otherMtms = @("9043-MRX", "9080-HEX", "9009-42A", "9009-22A")
$contaminated = $false
foreach ($mtm in $otherMtms) {
    if ($scrapeResponse.full_text -match $mtm) {
        Write-Host "✗ WARNING: Found reference to other MTM: $mtm" -ForegroundColor Yellow
        $contaminated = $true
    }
}
if (-not $contaminated) {
    Write-Host "✓ No mixed MTM contamination detected" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== E980 Ingestion Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Query lifecycle: test-e980-lifecycle-query.ps1" -ForegroundColor Gray
Write-Host "2. Query activations: test-e980-activation-query.ps1" -ForegroundColor Gray
Write-Host "3. Inspect chunks: Check e980-ingestion-response.json" -ForegroundColor Gray

# Made with Bob
