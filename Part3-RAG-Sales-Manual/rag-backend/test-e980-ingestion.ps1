# Test E980 Ingestion Workflow
# Complete workflow to test scraper, ingest E980, and validate results

Write-Host "E980 Test Ingestion Workflow" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: IBM Power System E980" -ForegroundColor White
Write-Host "MTM: 9080-M9S" -ForegroundColor White
Write-Host "Expected Collection: rag_mtm_9080_m9s" -ForegroundColor White
Write-Host "Sales Manual: https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s" -ForegroundColor White
Write-Host ""

# Configuration
$SERVER_NAME = "E980"
$MTM = "9080-M9S"
$SALES_MANUAL_URL = "https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s"
$EXPECTED_COLLECTION = "rag_mtm_9080_m9s"

# Step 1: Check if scraper service is accessible
Write-Host "Step 1: Testing Scraper Service" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow
Write-Host ""

Write-Host "Please provide the scraper service URL from IBM Code Engine:" -ForegroundColor Cyan
Write-Host "Example: https://scraper-service-xxxxx.us-south.codeengine.appdomain.cloud" -ForegroundColor Gray
$SCRAPER_URL = Read-Host "Scraper URL"

if (-not $SCRAPER_URL) {
    Write-Host "Error: Scraper URL is required" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Testing scraper service health..." -ForegroundColor Yellow

try {
    $healthResponse = Invoke-RestMethod -Uri "$SCRAPER_URL/health" -Method Get -TimeoutSec 10
    Write-Host "✓ Scraper service is healthy" -ForegroundColor Green
    Write-Host "  Status: $($healthResponse.status)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Scraper service is not accessible" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure:" -ForegroundColor Yellow
    Write-Host "  1. You are logged into IBM Cloud" -ForegroundColor White
    Write-Host "  2. The scraper service is running in Code Engine" -ForegroundColor White
    Write-Host "  3. The URL is correct and accessible" -ForegroundColor White
    exit 1
}

# Step 2: Test scraping E980
Write-Host ""
Write-Host "Step 2: Scraping E980 Sales Manual" -ForegroundColor Yellow
Write-Host "===================================" -ForegroundColor Yellow
Write-Host ""

Write-Host "Scraping $SALES_MANUAL_URL..." -ForegroundColor Yellow
Write-Host "This may take 30-60 seconds..." -ForegroundColor Gray
Write-Host ""

try {
    $scrapeBody = @{
        url = $SALES_MANUAL_URL
    } | ConvertTo-Json

    $scrapeResponse = Invoke-RestMethod -Uri "$SCRAPER_URL/scrape" -Method Post -Body $scrapeBody -ContentType "application/json" -TimeoutSec 120
    
    Write-Host "✓ Scraping completed successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Scraped Content Summary:" -ForegroundColor Cyan
    Write-Host "  Total Length: $($scrapeResponse.content.Length) characters" -ForegroundColor White
    Write-Host "  Has Tables: $($scrapeResponse.content -match '\|.*\|')" -ForegroundColor White
    Write-Host "  Has Feature Codes: $($scrapeResponse.content -match '#[A-Z0-9]{4}')" -ForegroundColor White
    
    # Check for lifecycle table
    if ($scrapeResponse.content -match "Product life cycle dates") {
        Write-Host "  ✓ Found 'Product life cycle dates' section" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ 'Product life cycle dates' section not found" -ForegroundColor Yellow
    }
    
    # Check for activation features
    $activationMatches = [regex]::Matches($scrapeResponse.content, "#([A-Z0-9]{4})")
    $featureCodes = $activationMatches | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
    Write-Host "  Feature Codes Found: $($featureCodes.Count)" -ForegroundColor White
    if ($featureCodes.Count -gt 0) {
        Write-Host "    Examples: $($featureCodes[0..([Math]::Min(4, $featureCodes.Count-1))] -join ', ')" -ForegroundColor Gray
    }
    
    # Save scraped content for inspection
    $scrapeResponse.content | Out-File -FilePath "e980_scraped_content.txt" -Encoding UTF8
    Write-Host ""
    Write-Host "  Saved to: e980_scraped_content.txt" -ForegroundColor Gray
    
} catch {
    Write-Host "✗ Scraping failed" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Find rag-backend pod
Write-Host ""
Write-Host "Step 3: Preparing Backend for Ingestion" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

$pod = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>$null

if (-not $pod) {
    Write-Host "✗ rag-backend pod not found" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found rag-backend pod: $pod" -ForegroundColor Green

# Step 4: Check if collection already exists
Write-Host ""
Write-Host "Step 4: Checking Collection Status" -ForegroundColor Yellow
Write-Host "===================================" -ForegroundColor Yellow
Write-Host ""

$checkScript = @"
import os
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

collection_name = '$EXPECTED_COLLECTION'

if client.indices.exists(index=collection_name):
    doc_count = client.count(index=collection_name)['count']
    print('EXISTS:{}'.format(doc_count))
else:
    print('NOT_EXISTS')
"@

$tempFile = [System.IO.Path]::GetTempFileName() + ".py"
$checkScript | Out-File -FilePath $tempFile -Encoding UTF8

try {
    $result = Get-Content $tempFile | oc exec -i $pod -- python 2>&1 | Select-String -Pattern "EXISTS|NOT_EXISTS"
    
    if ($result -match "EXISTS:(\d+)") {
        $docCount = $Matches[1]
        Write-Host "⚠ Collection already exists with $docCount documents" -ForegroundColor Yellow
        Write-Host ""
        $response = Read-Host "Delete existing collection and re-ingest? (yes/no)"
        
        if ($response -ne "yes") {
            Write-Host "Ingestion cancelled" -ForegroundColor Yellow
            exit 0
        }
        
        Write-Host ""
        Write-Host "Deleting existing collection..." -ForegroundColor Yellow
        
        $deleteScript = @"
import os
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

client.indices.delete(index='$EXPECTED_COLLECTION')
print('DELETED')
"@
        
        $deleteFile = [System.IO.Path]::GetTempFileName() + ".py"
        $deleteScript | Out-File -FilePath $deleteFile -Encoding UTF8
        Get-Content $deleteFile | oc exec -i $pod -- python 2>&1 | Out-Null
        Remove-Item $deleteFile -ErrorAction SilentlyContinue
        
        Write-Host "✓ Collection deleted" -ForegroundColor Green
    } else {
        Write-Host "✓ Collection does not exist (ready for fresh ingestion)" -ForegroundColor Green
    }
} finally {
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

# Step 5: Ingest E980
Write-Host ""
Write-Host "Step 5: Ingesting E980 into OpenSearch" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Yellow
Write-Host ""

Write-Host "Finding rag-backend service URL..." -ForegroundColor Yellow
$backendRoute = oc get route rag-backend-route -o jsonpath='{.spec.host}' 2>$null

if (-not $backendRoute) {
    Write-Host "✗ rag-backend route not found" -ForegroundColor Red
    exit 1
}

$BACKEND_URL = "http://$backendRoute"
Write-Host "✓ Backend URL: $BACKEND_URL" -ForegroundColor Green
Write-Host ""

Write-Host "Ingesting E980 sales manual..." -ForegroundColor Yellow
Write-Host "This will:" -ForegroundColor Cyan
Write-Host "  1. Create collection: $EXPECTED_COLLECTION" -ForegroundColor White
Write-Host "  2. Chunk the sales manual content" -ForegroundColor White
Write-Host "  3. Generate embeddings for each chunk" -ForegroundColor White
Write-Host "  4. Store in OpenSearch" -ForegroundColor White
Write-Host ""
Write-Host "This may take 2-3 minutes..." -ForegroundColor Gray
Write-Host ""

try {
    $ingestBody = @{
        pdf_url = $SALES_MANUAL_URL
        collection_name = $MTM
    } | ConvertTo-Json

    $ingestResponse = Invoke-RestMethod -Uri "$BACKEND_URL/api/load-pdf-from-url" -Method Post -Body $ingestBody -ContentType "application/json" -TimeoutSec 300
    
    Write-Host "✓ Ingestion completed successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ingestion Results:" -ForegroundColor Cyan
    Write-Host "  Collection: $($ingestResponse.collection)" -ForegroundColor White
    Write-Host "  Chunks Created: $($ingestResponse.chunks)" -ForegroundColor White
    Write-Host "  URL: $($ingestResponse.url)" -ForegroundColor White
    
} catch {
    Write-Host "✗ Ingestion failed" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check backend logs:" -ForegroundColor Yellow
    Write-Host "  oc logs $pod" -ForegroundColor White
    exit 1
}

# Step 6: Validate ingestion
Write-Host ""
Write-Host "Step 6: Validating Ingestion Quality" -ForegroundColor Yellow
Write-Host "=====================================" -ForegroundColor Yellow
Write-Host ""

Write-Host "Running validation checks..." -ForegroundColor Yellow

$validationScript = @"
import os
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

collection_name = '$EXPECTED_COLLECTION'

print('Validation Results:')
print('==================')
print('')

# Check 1: Document count
doc_count = client.count(index=collection_name)['count']
print('1. Document Count: {}'.format(doc_count))
if doc_count > 0:
    print('   Status: PASS')
else:
    print('   Status: FAIL - No documents found')

print('')

# Check 2: Search for lifecycle table
lifecycle_search = client.search(
    index=collection_name,
    body={
        'size': 1,
        'query': {
            'match': {'text': 'Product life cycle dates'}
        }
    }
)

lifecycle_found = lifecycle_search['hits']['total']['value'] > 0
print('2. Lifecycle Table: {}'.format('FOUND' if lifecycle_found else 'NOT FOUND'))
if lifecycle_found:
    print('   Status: PASS')
    # Show preview
    chunk_text = lifecycle_search['hits']['hits'][0]['_source']['text']
    lines = chunk_text.split('\n')
    print('   Preview (first 5 lines):')
    for line in lines[:5]:
        if line.strip():
            print('     {}'.format(line[:80]))
else:
    print('   Status: FAIL - Lifecycle table not found')

print('')

# Check 3: Search for activation features
activation_search = client.search(
    index=collection_name,
    body={
        'size': 10,
        'query': {
            'bool': {
                'should': [
                    {'match': {'text': 'activation'}},
                    {'match': {'text': 'processor activation'}},
                    {'match': {'text': 'memory activation'}}
                ]
            }
        }
    }
)

activation_count = activation_search['hits']['total']['value']
print('3. Activation Features: {} chunks found'.format(activation_count))
if activation_count > 0:
    print('   Status: PASS')
    # Extract feature codes
    import re
    feature_codes = set()
    for hit in activation_search['hits']['hits']:
        text = hit['_source']['text']
        codes = re.findall(r'#([A-Z0-9]{4})', text)
        feature_codes.update(codes)
    
    if feature_codes:
        print('   Feature codes found: {}'.format(', '.join(sorted(list(feature_codes))[:10])))
else:
    print('   Status: WARNING - No activation features found')

print('')

# Check 4: Check for mixed MTMs
mixed_mtm_search = client.search(
    index=collection_name,
    body={
        'size': 5,
        'query': {
            'bool': {
                'should': [
                    {'match': {'text': '9080-HEX'}},
                    {'match': {'text': '9043-MRX'}},
                    {'match': {'text': '9043-MRU'}}
                ]
            }
        }
    }
)

mixed_mtm_count = mixed_mtm_search['hits']['total']['value']
print('4. Mixed MTM Check: {} chunks with other MTMs'.format(mixed_mtm_count))
if mixed_mtm_count == 0:
    print('   Status: PASS - No mixed MTMs detected')
else:
    print('   Status: WARNING - Found references to other MTMs')
    for hit in mixed_mtm_search['hits']['hits']:
        text = hit['_source']['text'][:200]
        print('     {}'.format(text))

print('')
print('==================')
print('Validation Complete')
"@

$validationFile = [System.IO.Path]::GetTempFileName() + ".py"
$validationScript | Out-File -FilePath $validationFile -Encoding UTF8

try {
    Get-Content $validationFile | oc exec -i $pod -- python
} finally {
    Remove-Item $validationFile -ErrorAction SilentlyContinue
}

# Step 7: Test activation query
Write-Host ""
Write-Host "Step 7: Testing Activation Query" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow
Write-Host ""

Write-Host "Querying: 'What activation features are available for E980?'" -ForegroundColor Cyan
Write-Host ""

try {
    $queryBody = @{
        question = "What activation features are available for E980?"
        collection_name = $MTM
    } | ConvertTo-Json

    $queryResponse = Invoke-RestMethod -Uri "$BACKEND_URL/api/search" -Method Post -Body $queryBody -ContentType "application/json" -TimeoutSec 60
    
    if ($queryResponse.success) {
        Write-Host "✓ Query successful" -ForegroundColor Green
        Write-Host ""
        Write-Host "Query Type: $($queryResponse.query_type)" -ForegroundColor Cyan
        
        if ($queryResponse.query_type -eq "activation_lookup") {
            Write-Host "Features Found: $($queryResponse.count)" -ForegroundColor White
            Write-Host ""
            Write-Host "Summary:" -ForegroundColor Cyan
            Write-Host "  Total: $($queryResponse.summary.total)" -ForegroundColor White
            Write-Host "  Available: $($queryResponse.summary.available)" -ForegroundColor White
            Write-Host "  Discontinued: $($queryResponse.summary.discontinued)" -ForegroundColor White
            
            if ($queryResponse.features) {
                Write-Host ""
                Write-Host "First 5 Features:" -ForegroundColor Cyan
                $queryResponse.features[0..([Math]::Min(4, $queryResponse.features.Count-1))] | ForEach-Object {
                    Write-Host "  - #$($_.feature_code): $($_.description.Substring(0, [Math]::Min(60, $_.description.Length)))..." -ForegroundColor White
                }
            }
        }
    } else {
        Write-Host "⚠ Query returned no results" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "✗ Query failed" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  E980 INGESTION TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor White
Write-Host "  Server: $SERVER_NAME (MTM: $MTM)" -ForegroundColor Gray
Write-Host "  Collection: $EXPECTED_COLLECTION" -ForegroundColor Gray
Write-Host "  Scraped Content: e980_scraped_content.txt" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review validation results above" -ForegroundColor White
Write-Host "  2. Check e980_scraped_content.txt for quality" -ForegroundColor White
Write-Host "  3. If good, proceed with other servers" -ForegroundColor White
Write-Host "  4. If issues, adjust scraper/chunking and retry" -ForegroundColor White
Write-Host ""

# Made with Bob
