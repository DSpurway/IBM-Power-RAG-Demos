# Deploy Enhanced IBM Docs Scraper to IBM Cloud Code Engine
# Includes table preservation and metadata extraction

param(
    [string]$ProjectName = "scraper-service",
    [string]$AppName = "ibm-docs-scraper-enhanced",
    [string]$Region = "eu-gb",  # London/UK region
    [string]$ResourceGroup = ""  # Will prompt if not provided
)

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Deploying ENHANCED IBM Docs Scraper to IBM Cloud Code Engine" -ForegroundColor Cyan
Write-Host "Features: Table Preservation, Metadata Extraction, MTM Detection" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if IBM Cloud CLI is installed
Write-Host "Checking IBM Cloud CLI..." -ForegroundColor Cyan
$ibmcloudVersion = ibmcloud version 2>$null
if (-not $ibmcloudVersion) {
    Write-Host "  IBM Cloud CLI is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install it from:" -ForegroundColor Yellow
    Write-Host "  https://cloud.ibm.com/docs/cli?topic=cli-install-ibmcloud-cli" -ForegroundColor White
    Write-Host ""
    exit 1
}
Write-Host "  IBM Cloud CLI installed" -ForegroundColor Green
Write-Host ""

# Check if Code Engine plugin is installed
Write-Host "Checking Code Engine plugin..." -ForegroundColor Cyan
$cePlugin = ibmcloud plugin list 2>$null | Select-String "code-engine"
if (-not $cePlugin) {
    Write-Host "  Code Engine plugin not installed. Installing..." -ForegroundColor Yellow
    ibmcloud plugin install code-engine -f
    Write-Host "  Code Engine plugin installed" -ForegroundColor Green
} else {
    Write-Host "  Code Engine plugin installed" -ForegroundColor Green
}
Write-Host ""

# Check if logged in
Write-Host "Checking IBM Cloud login status..." -ForegroundColor Cyan
$loginStatus = ibmcloud target 2>&1
if ($loginStatus -match "Not logged in") {
    Write-Host "  Not logged in to IBM Cloud" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Logging in with SSO..." -ForegroundColor Yellow
    ibmcloud login --sso
}
Write-Host "  Logged in to IBM Cloud" -ForegroundColor Green
Write-Host ""

# Target region
Write-Host "Targeting region: $Region" -ForegroundColor Cyan
ibmcloud target -r $Region
Write-Host ""

# Select or create project
Write-Host "Selecting Code Engine project: $ProjectName" -ForegroundColor Cyan
$projectExists = ibmcloud ce project list 2>&1 | Select-String $ProjectName
if (-not $projectExists) {
    Write-Host "  Project does not exist. Creating..." -ForegroundColor Yellow
    ibmcloud ce project create --name $ProjectName
    Write-Host "  Project created" -ForegroundColor Green
}
ibmcloud ce project select --name $ProjectName
Write-Host "  Project selected" -ForegroundColor Green
Write-Host ""

# Build and deploy
Write-Host "Building and deploying enhanced scraper..." -ForegroundColor Cyan
Write-Host "  This will take 5-10 minutes..." -ForegroundColor Yellow
Write-Host ""

# Delete existing app if it exists
$appExists = ibmcloud ce app list 2>&1 | Select-String $AppName
if ($appExists) {
    Write-Host "  Deleting existing app..." -ForegroundColor Yellow
    ibmcloud ce app delete --name $AppName --force
    Start-Sleep -Seconds 5
}

# Build and deploy from source
ibmcloud ce app create `
    --name $AppName `
    --build-source . `
    --dockerfile Dockerfile.enhanced `
    --cpu 1 `
    --memory 2G `
    --min-scale 0 `
    --max-scale 1 `
    --port 8080 `
    --wait

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "Enhanced Scraper Deployed Successfully!" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host ""
    
    # Get the app URL
    $appUrl = ibmcloud ce app get --name $AppName --output json | ConvertFrom-Json | Select-Object -ExpandProperty status | Select-Object -ExpandProperty url
    
    Write-Host "App URL: $appUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Test endpoints:" -ForegroundColor Yellow
    Write-Host "  Health check: $appUrl/health" -ForegroundColor White
    Write-Host "  Scrape: $appUrl/scrape?url=https://www.ibm.com/docs/..." -ForegroundColor White
    Write-Host ""
    Write-Host "Enhanced Features:" -ForegroundColor Yellow
    Write-Host "  ✓ Tables preserved as Markdown" -ForegroundColor Green
    Write-Host "  ✓ Withdrawal dates extracted" -ForegroundColor Green
    Write-Host "  ✓ Feature codes extracted" -ForegroundColor Green
    Write-Host "  ✓ MTM detection" -ForegroundColor Green
    Write-Host "  ✓ Structured sections" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test the scraper with: curl $appUrl/health" -ForegroundColor White
    Write-Host "  2. Update backend SCRAPER_URL environment variable to: $appUrl" -ForegroundColor White
    Write-Host "  3. Re-run bulk ingestion to get enhanced data" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host "Deployment Failed!" -ForegroundColor Red
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the logs with:" -ForegroundColor Yellow
    Write-Host "  ibmcloud ce app logs --name $AppName" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Made with Bob
