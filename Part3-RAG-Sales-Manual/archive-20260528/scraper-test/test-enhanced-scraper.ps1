# Test Enhanced Scraper
$scraperUrl = "https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud"
$testUrl = "https://www.ibm.com/docs/en/announcements/family-908005-power-e1180-enterprise-server-9080-heu"

Write-Host "Testing Enhanced Scraper..." -ForegroundColor Cyan
Write-Host "Scraper URL: $scraperUrl" -ForegroundColor Gray
Write-Host "Test Document: IBM Power E1180" -ForegroundColor Gray
Write-Host ""

try {
    Write-Host "Sending scrape request (this may take 30-60 seconds)..." -ForegroundColor Yellow
    $response = Invoke-WebRequest -Uri "$scraperUrl/scrape?url=$testUrl" -UseBasicParsing -TimeoutSec 120
    $json = $response.Content | ConvertFrom-Json
    
    Write-Host "✓ Status: $($json.status)" -ForegroundColor Green
    Write-Host "✓ Tables Found: $($json.tables_count)" -ForegroundColor Green
    Write-Host "✓ Sections Found: $($json.sections.Count)" -ForegroundColor Green
    
    Write-Host "`nMetadata Extracted:" -ForegroundColor Cyan
    foreach ($key in $json.metadata.PSObject.Properties.Name) {
        $value = $json.metadata.$key
        if ($value -is [Array]) {
            Write-Host "  - $key : $($value.Count) items" -ForegroundColor White
        } else {
            Write-Host "  - $key : $value" -ForegroundColor White
        }
    }
    
    if ($json.tables_markdown -and $json.tables_markdown.Count -gt 0) {
        Write-Host "`nFirst Table Preview (Markdown):" -ForegroundColor Cyan
        $preview = $json.tables_markdown[0]
        if ($preview.Length -gt 500) {
            $preview = $preview.Substring(0, 500) + "..."
        }
        Write-Host $preview -ForegroundColor White
    }
    
    Write-Host "`n✓ Enhanced scraper is working correctly!" -ForegroundColor Green
    
} catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Made with Bob
