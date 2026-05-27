# Run E1080 Activation Test
# This script runs the test inside the rag-backend pod to show what's being retrieved

Write-Host "E1080 Activation Retrieval Test" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Find the rag-backend pod
Write-Host "Finding rag-backend pod..." -ForegroundColor Yellow
$pod = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>$null

if (-not $pod) {
    Write-Host "Error: rag-backend pod not found!" -ForegroundColor Red
    Write-Host "Make sure the backend is deployed and running." -ForegroundColor Red
    exit 1
}

Write-Host "Found pod: $pod" -ForegroundColor Green
Write-Host ""

# Copy the test script to the pod
Write-Host "Copying test script to pod..." -ForegroundColor Yellow
oc cp test_e1080_activation_simple.py ${pod}:/app/test_e1080_activation_simple.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to copy test script to pod" -ForegroundColor Red
    exit 1
}

Write-Host "Test script copied successfully" -ForegroundColor Green
Write-Host ""

# Run the test
Write-Host "Running E1080 activation test..." -ForegroundColor Yellow
Write-Host "This will show:" -ForegroundColor Cyan
Write-Host "  1. What chunks are retrieved from OpenSearch" -ForegroundColor Cyan
Write-Host "  2. What the activation service extracts" -ForegroundColor Cyan
Write-Host "  3. What goes to the LLM (if used)" -ForegroundColor Cyan
Write-Host "  4. What comes back as the final answer" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Write-Host ""

oc exec $pod -- python test_e1080_activation_simple.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Test encountered an error. Check the output above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Test completed successfully!" -ForegroundColor Green
Write-Host ""

# Copy results back
Write-Host "Copying results file back..." -ForegroundColor Yellow
oc cp ${pod}:/app/e1080_activation_test_results.json ./e1080_activation_test_results.json 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Results saved to: e1080_activation_test_results.json" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now review the JSON file for complete details:" -ForegroundColor Cyan
    Write-Host "  code e1080_activation_test_results.json" -ForegroundColor White
} else {
    Write-Host "Note: Could not copy results file (may not exist yet)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green

# Made with Bob
