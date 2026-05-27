# Get Code Engine Scraper Service URL
# Helps find and display the scraper service URL from IBM Code Engine

Write-Host "IBM Code Engine Scraper Service Finder" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Check if IBM Cloud CLI is installed
Write-Host "Checking for IBM Cloud CLI..." -ForegroundColor Yellow

try {
    $ibmcloudVersion = ibmcloud --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "IBM Cloud CLI not found"
    }
    Write-Host "✓ IBM Cloud CLI is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ IBM Cloud CLI is not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install IBM Cloud CLI:" -ForegroundColor Yellow
    Write-Host "  https://cloud.ibm.com/docs/cli?topic=cli-install-ibmcloud-cli" -ForegroundColor White
    Write-Host ""
    Write-Host "Or use the web console:" -ForegroundColor Yellow
    Write-Host "  1. Go to https://cloud.ibm.com/codeengine/projects" -ForegroundColor White
    Write-Host "  2. Select your project" -ForegroundColor White
    Write-Host "  3. Click on 'Applications'" -ForegroundColor White
    Write-Host "  4. Find the scraper application" -ForegroundColor White
    Write-Host "  5. Copy the 'Public URL'" -ForegroundColor White
    exit 1
}

Write-Host ""

# Check if logged in
Write-Host "Checking IBM Cloud login status..." -ForegroundColor Yellow

$loginCheck = ibmcloud target 2>&1 | Out-String

if ($loginCheck -match "Not logged in") {
    Write-Host "✗ Not logged into IBM Cloud" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please log in:" -ForegroundColor Yellow
    Write-Host "  ibmcloud login --sso" -ForegroundColor White
    Write-Host ""
    Write-Host "Or use API key:" -ForegroundColor Yellow
    Write-Host "  ibmcloud login --apikey YOUR_API_KEY" -ForegroundColor White
    Write-Host ""
    
    $response = Read-Host "Would you like to log in now? (yes/no)"
    if ($response -eq "yes") {
        Write-Host ""
        Write-Host "Logging in with SSO..." -ForegroundColor Yellow
        ibmcloud login --sso
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ Login failed" -ForegroundColor Red
            exit 1
        }
    } else {
        exit 1
    }
}

Write-Host "✓ Logged into IBM Cloud" -ForegroundColor Green

# Show current target
$targetInfo = ibmcloud target 2>&1 | Out-String
if ($targetInfo -match "Region:\s+(\S+)") {
    $region = $Matches[1]
    Write-Host "  Region: $region" -ForegroundColor Gray
}
if ($targetInfo -match "Resource group:\s+(.+)") {
    $resourceGroup = $Matches[1].Trim()
    Write-Host "  Resource Group: $resourceGroup" -ForegroundColor Gray
}

Write-Host ""

# Check if Code Engine plugin is installed
Write-Host "Checking for Code Engine plugin..." -ForegroundColor Yellow

$plugins = ibmcloud plugin list 2>&1 | Out-String

if ($plugins -notmatch "code-engine") {
    Write-Host "✗ Code Engine plugin not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing Code Engine plugin..." -ForegroundColor Yellow
    ibmcloud plugin install code-engine
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to install Code Engine plugin" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Code Engine plugin installed" -ForegroundColor Green
} else {
    Write-Host "✓ Code Engine plugin is installed" -ForegroundColor Green
}

Write-Host ""

# List Code Engine projects
Write-Host "Finding Code Engine projects..." -ForegroundColor Yellow
Write-Host ""

$projects = ibmcloud ce project list --output json 2>&1 | ConvertFrom-Json

if (-not $projects -or $projects.Count -eq 0) {
    Write-Host "✗ No Code Engine projects found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create a Code Engine project first:" -ForegroundColor Yellow
    Write-Host "  https://cloud.ibm.com/codeengine/projects" -ForegroundColor White
    exit 1
}

Write-Host "Found $($projects.Count) Code Engine project(s):" -ForegroundColor Green
Write-Host ""

for ($i = 0; $i -lt $projects.Count; $i++) {
    $project = $projects[$i]
    Write-Host "  [$($i+1)] $($project.name)" -ForegroundColor White
    Write-Host "      Region: $($project.region)" -ForegroundColor Gray
    Write-Host "      ID: $($project.id)" -ForegroundColor Gray
    Write-Host ""
}

# Select project
if ($projects.Count -eq 1) {
    $selectedProject = $projects[0]
    Write-Host "Using project: $($selectedProject.name)" -ForegroundColor Cyan
} else {
    $selection = Read-Host "Select project number (1-$($projects.Count))"
    $selectedProject = $projects[[int]$selection - 1]
    Write-Host "Selected: $($selectedProject.name)" -ForegroundColor Cyan
}

Write-Host ""

# Select the project
Write-Host "Selecting project..." -ForegroundColor Yellow
ibmcloud ce project select --name $selectedProject.name 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to select project" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Project selected" -ForegroundColor Green
Write-Host ""

# List applications
Write-Host "Finding scraper application..." -ForegroundColor Yellow
Write-Host ""

$apps = ibmcloud ce application list --output json 2>&1 | ConvertFrom-Json

if (-not $apps -or $apps.Count -eq 0) {
    Write-Host "✗ No applications found in this project" -ForegroundColor Red
    Write-Host ""
    Write-Host "The scraper service may not be deployed yet." -ForegroundColor Yellow
    Write-Host "Deploy it using:" -ForegroundColor Yellow
    Write-Host "  cd Part3-RAG-Sales-Manual/scraper-test" -ForegroundColor White
    Write-Host "  ./deploy-to-code-engine.ps1" -ForegroundColor White
    exit 1
}

Write-Host "Found $($apps.Count) application(s):" -ForegroundColor Green
Write-Host ""

$scraperApp = $null

foreach ($app in $apps) {
    Write-Host "  Application: $($app.name)" -ForegroundColor White
    Write-Host "    Status: $($app.status)" -ForegroundColor Gray
    Write-Host "    URL: $($app.url)" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if this looks like the scraper
    if ($app.name -match "scraper" -or $app.name -match "simple") {
        $scraperApp = $app
    }
}

# If we found a scraper app, use it
if ($scraperApp) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  SCRAPER SERVICE FOUND" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Application: $($scraperApp.name)" -ForegroundColor White
    Write-Host "Status: $($scraperApp.status)" -ForegroundColor White
    Write-Host ""
    Write-Host "Scraper URL:" -ForegroundColor Yellow
    Write-Host "  $($scraperApp.url)" -ForegroundColor Green
    Write-Host ""
    
    # Test the scraper
    Write-Host "Testing scraper health endpoint..." -ForegroundColor Yellow
    
    try {
        $healthResponse = Invoke-RestMethod -Uri "$($scraperApp.url)/health" -Method Get -TimeoutSec 10
        Write-Host "✓ Scraper is healthy!" -ForegroundColor Green
        Write-Host "  Status: $($healthResponse.status)" -ForegroundColor Gray
        Write-Host ""
    } catch {
        Write-Host "⚠ Could not reach scraper health endpoint" -ForegroundColor Yellow
        Write-Host "  Error: $_" -ForegroundColor Gray
        Write-Host "  The service may still be starting up" -ForegroundColor Gray
        Write-Host ""
    }
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Copy this URL for the E980 ingestion test:" -ForegroundColor Yellow
    Write-Host "  $($scraperApp.url)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next step:" -ForegroundColor Yellow
    Write-Host "  ./test-e980-ingestion.ps1" -ForegroundColor White
    Write-Host ""
    
    # Save to file for easy access
    $scraperApp.url | Out-File -FilePath "scraper-url.txt" -Encoding UTF8
    Write-Host "URL saved to: scraper-url.txt" -ForegroundColor Gray
    
} else {
    Write-Host "⚠ No scraper application found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Available applications:" -ForegroundColor Yellow
    foreach ($app in $apps) {
        Write-Host "  - $($app.name): $($app.url)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "If one of these is your scraper, use its URL." -ForegroundColor Yellow
    Write-Host "Otherwise, deploy the scraper first:" -ForegroundColor Yellow
    Write-Host "  cd Part3-RAG-Sales-Manual/scraper-test" -ForegroundColor White
    Write-Host "  ./deploy-to-code-engine.ps1" -ForegroundColor White
}

Write-Host ""

# Made with Bob
