# Test Activation Feature LLM Enhancement
# This script tests the new LLM-based description generation

Write-Host "`n=== Testing Activation Feature LLM Enhancement ===" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "activation_feature_service.py")) {
    Write-Host "Error: Must run from rag-backend directory" -ForegroundColor Red
    exit 1
}

# Set environment variables for local testing (adjust as needed)
$env:GRANITE_HOST = "localhost"
$env:GRANITE_PORT = "8080"

Write-Host "`nEnvironment Configuration:" -ForegroundColor Yellow
Write-Host "  GRANITE_HOST: $env:GRANITE_HOST"
Write-Host "  GRANITE_PORT: $env:GRANITE_PORT"

# Run the test script
Write-Host "`nRunning test script..." -ForegroundColor Yellow
python test_activation_llm.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Tests completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Tests failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan

# Made with Bob
