# Set SCRAPER_URL environment variable in backend deployment
# This points the backend to the Code Engine scraper service

param(
    [Parameter(Mandatory=$true)]
    [string]$ScraperUrl
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setting SCRAPER_URL in Backend" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Scraper URL: $ScraperUrl" -ForegroundColor Yellow

# Set the environment variable
Write-Host ""
Write-Host "Updating deployment..." -ForegroundColor Yellow

oc set env deployment/rag-backend SCRAPER_URL="$ScraperUrl"

Write-Host ""
Write-Host "✓ Environment variable set" -ForegroundColor Green

Write-Host ""
Write-Host "Waiting for rollout to complete..." -ForegroundColor Yellow
oc rollout status deployment/rag-backend

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Configuration Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "You can now trigger bulk ingestion from the UI or use:" -ForegroundColor Yellow
Write-Host "  .\test-s922-ingestion.ps1" -ForegroundColor White

# Made with Bob
