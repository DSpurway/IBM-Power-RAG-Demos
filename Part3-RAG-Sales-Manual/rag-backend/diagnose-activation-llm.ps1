# Diagnostic script to check what Granite LLM is producing for activation features
# This helps us understand if Granite is adding value or just echoing the Sales Manual

Write-Host "=== Activation Feature LLM Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# Get the backend route
Write-Host "Getting backend route..." -ForegroundColor Yellow
$BACKEND_ROUTE = oc get route rag-backend-service -o jsonpath='{.spec.host}' 2>$null

if (-not $BACKEND_ROUTE) {
    Write-Host "Error: Could not find rag-backend-service route" -ForegroundColor Red
    Write-Host "Make sure the backend is deployed" -ForegroundColor Red
    exit 1
}

Write-Host "Backend URL: https://$BACKEND_ROUTE" -ForegroundColor Green
Write-Host ""

# Get available collections
Write-Host "Fetching available collections..." -ForegroundColor Yellow
$collectionsResponse = Invoke-RestMethod -Uri "https://$BACKEND_ROUTE/api/collections" -Method Get -SkipCertificateCheck

Write-Host "Available collections:" -ForegroundColor Green
$collectionsResponse.collections | ForEach-Object {
    Write-Host "  - $($_.name) ($($_.count) documents)" -ForegroundColor White
}
Write-Host ""

# Ask user to select a collection
Write-Host "Enter collection name to test (or press Enter for first sales manual collection):" -ForegroundColor Yellow
$selectedCollection = Read-Host

if (-not $selectedCollection) {
    # Find first sales manual collection
    $selectedCollection = $collectionsResponse.collections | Where-Object { $_.name -like "rag_*" -or $_.name -like "*sales*" } | Select-Object -First 1 -ExpandProperty name
    Write-Host "Using: $selectedCollection" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Testing Activation Query ===" -ForegroundColor Cyan
Write-Host ""

# Test query
$query = "What processor activations are available?"
Write-Host "Query: $query" -ForegroundColor Yellow
Write-Host ""

# Make the search request
Write-Host "Sending search request..." -ForegroundColor Yellow
$searchBody = @{
    question = $query
    collection_name = $selectedCollection
    k = 10
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "https://$BACKEND_ROUTE/api/search" -Method Post -Body $searchBody -ContentType "application/json" -SkipCertificateCheck
    
    Write-Host "=== RESPONSE ANALYSIS ===" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if it's an activation lookup
    if ($response.query_type -eq "activation_lookup") {
        Write-Host "✓ Query correctly classified as activation_lookup" -ForegroundColor Green
        Write-Host ""
        
        # Show summary
        Write-Host "Summary:" -ForegroundColor Yellow
        Write-Host "  Total features: $($response.summary.total)" -ForegroundColor White
        Write-Host "  Available: $($response.summary.available)" -ForegroundColor Green
        Write-Host "  Discontinued: $($response.summary.discontinued)" -ForegroundColor Red
        Write-Host "  Chunks searched: $($response.chunks_searched)" -ForegroundColor White
        Write-Host ""
        
        # Show features
        if ($response.features -and $response.features.Count -gt 0) {
            Write-Host "=== FEATURES FOUND ===" -ForegroundColor Cyan
            Write-Host ""
            
            $response.features | ForEach-Object {
                Write-Host "Feature: #$($_.feature_code)" -ForegroundColor Yellow
                Write-Host "Status: $($_.status)" -ForegroundColor $(if ($_.is_available) { "Green" } else { "Red" })
                Write-Host "Description:" -ForegroundColor White
                Write-Host "  $($_.description)" -ForegroundColor White
                Write-Host ""
                
                # Show a snippet of the raw chunk for comparison
                if ($_.metadata.chunk_text) {
                    $chunkSnippet = $_.metadata.chunk_text.Substring(0, [Math]::Min(300, $_.metadata.chunk_text.Length))
                    Write-Host "Raw chunk (first 300 chars):" -ForegroundColor DarkGray
                    Write-Host "  $chunkSnippet..." -ForegroundColor DarkGray
                    Write-Host ""
                }
                Write-Host "---" -ForegroundColor DarkGray
                Write-Host ""
            }
        } else {
            Write-Host "No features found" -ForegroundColor Red
        }
        
        # Show the formatted answer
        Write-Host "=== FORMATTED ANSWER ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host $response.answer -ForegroundColor White
        Write-Host ""
        
    } else {
        Write-Host "Query type: $($response.query_type)" -ForegroundColor Yellow
        Write-Host "This is not an activation lookup query" -ForegroundColor Red
    }
    
    # Save full response for detailed analysis
    $outputFile = "activation-diagnostic-output.json"
    $response | ConvertTo-Json -Depth 10 | Out-File $outputFile
    Write-Host "Full response saved to: $outputFile" -ForegroundColor Green
    
} catch {
    Write-Host "Error making request:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Response body (if available):" -ForegroundColor Yellow
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor White
    }
}

Write-Host ""
Write-Host "=== DIAGNOSTIC COMPLETE ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Compare the 'Description' with the 'Raw chunk' for each feature" -ForegroundColor White
Write-Host "2. Check if Granite is adding value or just echoing the chunk" -ForegroundColor White
Write-Host "3. Look at activation-diagnostic-output.json for full details" -ForegroundColor White

# Made with Bob
