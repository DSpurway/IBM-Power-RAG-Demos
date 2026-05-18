# Diagnose Backend 500 Error
# This script checks logs and configuration to identify the issue

Write-Host "`n=== Diagnosing RAG Backend Error ===" -ForegroundColor Cyan

# Step 1: Check if pod is running
Write-Host "`nStep 1: Checking pod status..." -ForegroundColor Yellow
$POD = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>$null

if ([string]::IsNullOrEmpty($POD)) {
    Write-Host "Error: No rag-backend pod found!" -ForegroundColor Red
    Write-Host "Run: oc get pods" -ForegroundColor Yellow
    exit 1
}

Write-Host "Pod: $POD" -ForegroundColor Green

$POD_STATUS = oc get pod $POD -o jsonpath='{.status.phase}'
Write-Host "Status: $POD_STATUS" -ForegroundColor $(if ($POD_STATUS -eq "Running") { "Green" } else { "Red" })

# Step 2: Check recent logs for errors
Write-Host "`nStep 2: Checking recent logs for errors..." -ForegroundColor Yellow
Write-Host "Last 50 lines of logs:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Gray

oc logs $POD --tail=50 | Select-String -Pattern "error|Error|ERROR|exception|Exception|EXCEPTION|traceback|Traceback|TRACEBACK|failed|Failed|FAILED" -Context 2,2

# Step 3: Check if services are accessible
Write-Host "`n`nStep 3: Checking service connectivity..." -ForegroundColor Yellow

# Check OpenSearch
Write-Host "`nTesting OpenSearch connection..." -ForegroundColor Cyan
oc exec $POD -- curl -s -o /dev/null -w "%{http_code}" http://opensearch-service:9200 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OpenSearch: Accessible" -ForegroundColor Green
} else {
    Write-Host "  OpenSearch: Not accessible" -ForegroundColor Red
}

# Check Granite
Write-Host "Testing Granite LLM connection..." -ForegroundColor Cyan
oc exec $POD -- curl -s -o /dev/null -w "%{http_code}" http://granite-llama-service:8080/health 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Granite LLM: Accessible" -ForegroundColor Green
} else {
    Write-Host "  Granite LLM: Not accessible" -ForegroundColor Red
}

# Step 4: Check environment variables
Write-Host "`nStep 4: Checking environment variables..." -ForegroundColor Yellow
Write-Host "Key environment variables:" -ForegroundColor Cyan

$ENV_VARS = @(
    "OPENSEARCH_HOST",
    "OPENSEARCH_PORT",
    "GRANITE_HOST",
    "GRANITE_PORT",
    "WATSON_ASSISTANT_API_KEY",
    "WATSON_ASSISTANT_URL"
)

foreach ($VAR in $ENV_VARS) {
    $VALUE = oc exec $POD -- printenv $VAR 2>$null
    if ([string]::IsNullOrEmpty($VALUE)) {
        Write-Host "  $VAR : NOT SET" -ForegroundColor Red
    } else {
        if ($VAR -like "*KEY*" -or $VAR -like "*PASSWORD*") {
            Write-Host "  $VAR : ****** (set)" -ForegroundColor Green
        } else {
            Write-Host "  $VAR : $VALUE" -ForegroundColor Green
        }
    }
}

# Step 5: Show full recent logs
Write-Host "`nStep 5: Full recent logs (last 100 lines)..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Gray
oc logs $POD --tail=100

Write-Host "`n========================================" -ForegroundColor Gray

# Step 6: Recommendations
Write-Host "`nStep 6: Recommendations..." -ForegroundColor Yellow

Write-Host "`nTo see live logs, run:" -ForegroundColor Cyan
Write-Host "  oc logs -f $POD" -ForegroundColor White

Write-Host "`nTo test the backend directly:" -ForegroundColor Cyan
Write-Host "  oc exec $POD -- curl -X POST http://localhost:5000/health" -ForegroundColor White

Write-Host "`nTo restart the pod:" -ForegroundColor Cyan
Write-Host "  oc delete pod $POD" -ForegroundColor White

Write-Host "`n=== Diagnosis Complete ===" -ForegroundColor Cyan

# Made with Bob
