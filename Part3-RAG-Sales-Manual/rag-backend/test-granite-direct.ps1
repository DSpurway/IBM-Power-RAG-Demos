# Test Granite service directly to understand its capabilities
# This helps us see if the problem is with Granite itself or our prompts

Write-Host "=== Granite Service Direct Test ===" -ForegroundColor Cyan
Write-Host ""

# Get the Granite route
Write-Host "Getting Granite service route..." -ForegroundColor Yellow
$GRANITE_ROUTE = oc get route granite-service -o jsonpath='{.spec.host}' 2>$null

if (-not $GRANITE_ROUTE) {
    Write-Host "Error: Could not find granite-service route" -ForegroundColor Red
    Write-Host "Trying internal service name..." -ForegroundColor Yellow
    
    # Try to get a backend pod to test from inside the cluster
    $POD = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>$null
    
    if (-not $POD) {
        Write-Host "Error: Could not find backend pod either" -ForegroundColor Red
        Write-Host "Make sure granite-service and rag-backend are deployed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Using internal service via pod: $POD" -ForegroundColor Green
    $useInternal = $true
} else {
    Write-Host "Granite URL: https://$GRANITE_ROUTE" -ForegroundColor Green
    $useInternal = $false
}

Write-Host ""

# Sample activation feature text from Sales Manual
$sampleChunk = @"
(#EDPB) 1-core Processor Activation for EDP2 (Pools 2.0)

Attributes provided: Processor

Minimum required: 1

Maximum allowed: 24

OS level required: All

Initial order/MES/Both/Supported: Both

CSU: No

Return parts MES: None
"@

Write-Host "=== Test 1: Simple Summarization ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Sample chunk:" -ForegroundColor Yellow
Write-Host $sampleChunk -ForegroundColor White
Write-Host ""

$prompt1 = @"
Based on the following IBM Power Systems sales manual excerpt for feature code #EDPB, provide exactly one short sentence describing what this activation feature is for.

Sales Manual Excerpt:
$sampleChunk

Requirements:
- Return exactly one sentence
- Maximum 25 words
- State the activation type and capacity/amount
- Include only the most important restriction if present
- Do not include the feature code
- Do not add explanations, headings, or extra text

Description:
"@

Write-Host "Prompt being sent:" -ForegroundColor Yellow
Write-Host $prompt1 -ForegroundColor DarkGray
Write-Host ""

$requestBody = @{
    prompt = $prompt1
    max_tokens = 32
    temperature = 0.1
    stop = @("`n", "`n`n", "Feature Code:", "Sales Manual", "Description:")
} | ConvertTo-Json

Write-Host "Sending request to Granite..." -ForegroundColor Yellow

try {
    if ($useInternal) {
        # Execute from inside a pod
        $escapedBody = $requestBody -replace '"', '\"'
        $curlCmd = "curl -s -X POST http://granite-service:8080/v1/completions -H 'Content-Type: application/json' -d `"$escapedBody`""
        $responseJson = oc exec $POD -- sh -c $curlCmd
        $response = $responseJson | ConvertFrom-Json
    } else {
        $response = Invoke-RestMethod -Uri "https://$GRANITE_ROUTE/v1/completions" -Method Post -Body $requestBody -ContentType "application/json" -SkipCertificateCheck
    }
    
    Write-Host "=== GRANITE RESPONSE ===" -ForegroundColor Green
    Write-Host ""
    
    if ($response.choices -and $response.choices.Count -gt 0) {
        $generatedText = $response.choices[0].text.Trim()
        Write-Host "Generated description:" -ForegroundColor Yellow
        Write-Host "  $generatedText" -ForegroundColor White
        Write-Host ""
        
        # Analysis
        Write-Host "Analysis:" -ForegroundColor Cyan
        Write-Host "  Length: $($generatedText.Length) characters" -ForegroundColor White
        Write-Host "  Word count: $(($generatedText -split '\s+').Count) words" -ForegroundColor White
        
        # Check if it's just echoing the input
        $similarity = 0
        $chunkWords = ($sampleChunk -split '\s+' | Where-Object { $_.Length -gt 3 })
        $genWords = ($generatedText -split '\s+' | Where-Object { $_.Length -gt 3 })
        
        foreach ($word in $genWords) {
            if ($chunkWords -contains $word) {
                $similarity++
            }
        }
        
        $similarityPercent = if ($genWords.Count -gt 0) { [math]::Round(($similarity / $genWords.Count) * 100, 1) } else { 0 }
        Write-Host "  Word overlap with source: $similarityPercent%" -ForegroundColor White
        
        if ($similarityPercent -gt 80) {
            Write-Host "  ⚠️  HIGH OVERLAP - Granite may be mostly echoing the source" -ForegroundColor Red
        } elseif ($similarityPercent -gt 50) {
            Write-Host "  ⚠️  MODERATE OVERLAP - Some transformation but limited" -ForegroundColor Yellow
        } else {
            Write-Host "  ✓ LOW OVERLAP - Good transformation" -ForegroundColor Green
        }
    } else {
        Write-Host "No response generated" -ForegroundColor Red
    }
    
    Write-Host ""
    
} catch {
    Write-Host "Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Test 2: Different Temperature ===" -ForegroundColor Cyan
Write-Host ""

$requestBody2 = @{
    prompt = $prompt1
    max_tokens = 32
    temperature = 0.7
    stop = @("`n", "`n`n", "Feature Code:", "Sales Manual", "Description:")
} | ConvertTo-Json

Write-Host "Testing with temperature=0.7 (more creative)..." -ForegroundColor Yellow

try {
    if ($useInternal) {
        $escapedBody = $requestBody2 -replace '"', '\"'
        $curlCmd = "curl -s -X POST http://granite-service:8080/v1/completions -H 'Content-Type: application/json' -d `"$escapedBody`""
        $responseJson = oc exec $POD -- sh -c $curlCmd
        $response = $responseJson | ConvertFrom-Json
    } else {
        $response = Invoke-RestMethod -Uri "https://$GRANITE_ROUTE/v1/completions" -Method Post -Body $requestBody2 -ContentType "application/json" -SkipCertificateCheck
    }
    
    if ($response.choices -and $response.choices.Count -gt 0) {
        $generatedText = $response.choices[0].text.Trim()
        Write-Host "Generated description:" -ForegroundColor Yellow
        Write-Host "  $generatedText" -ForegroundColor White
        Write-Host ""
    }
    
} catch {
    Write-Host "Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Test 3: Simpler Prompt ===" -ForegroundColor Cyan
Write-Host ""

$simplePrompt = "Summarize this IBM Power activation feature in one sentence: $sampleChunk`n`nSummary:"

Write-Host "Testing with simpler prompt..." -ForegroundColor Yellow

$requestBody3 = @{
    prompt = $simplePrompt
    max_tokens = 50
    temperature = 0.3
} | ConvertTo-Json

try {
    if ($useInternal) {
        $escapedBody = $requestBody3 -replace '"', '\"'
        $curlCmd = "curl -s -X POST http://granite-service:8080/v1/completions -H 'Content-Type: application/json' -d `"$escapedBody`""
        $responseJson = oc exec $POD -- sh -c $curlCmd
        $response = $responseJson | ConvertFrom-Json
    } else {
        $response = Invoke-RestMethod -Uri "https://$GRANITE_ROUTE/v1/completions" -Method Post -Body $requestBody3 -ContentType "application/json" -SkipCertificateCheck
    }
    
    if ($response.choices -and $response.choices.Count -gt 0) {
        $generatedText = $response.choices[0].text.Trim()
        Write-Host "Generated description:" -ForegroundColor Yellow
        Write-Host "  $generatedText" -ForegroundColor White
        Write-Host ""
    }
    
} catch {
    Write-Host "Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "=== DIAGNOSTIC COMPLETE ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Key Questions:" -ForegroundColor Yellow
Write-Host "1. Is Granite producing meaningful summaries or just echoing?" -ForegroundColor White
Write-Host "2. Does temperature affect the quality?" -ForegroundColor White
Write-Host "3. Does a simpler prompt work better?" -ForegroundColor White
Write-Host ""
Write-Host "If Granite is mostly echoing the source, we should:" -ForegroundColor Yellow
Write-Host "- Consider using manual extraction instead" -ForegroundColor White
Write-Host "- Or improve the prompt to force more transformation" -ForegroundColor White
Write-Host "- Or use a different model/approach" -ForegroundColor White

# Made with Bob
