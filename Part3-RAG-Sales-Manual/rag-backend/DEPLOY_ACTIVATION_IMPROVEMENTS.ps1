#!/usr/bin/env pwsh
# Deploy Activation Feature Improvements
# This script handles the complete deployment workflow

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Activation Feature Improvements Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if logged into OpenShift
try {
    $null = oc whoami 2>&1
} catch {
    Write-Host "Error: Not logged into OpenShift. Please run 'oc login' first." -ForegroundColor Red
    exit 1
}

$PROJECT = oc project -q
Write-Host "Working in project: $PROJECT" -ForegroundColor Green
Write-Host ""

# Ask user which deployment method to use
Write-Host "Choose deployment method:" -ForegroundColor Yellow
Write-Host "  1. Build from local directory (recommended for testing)" -ForegroundColor White
Write-Host "  2. Commit to GitHub and build from there (recommended for production)" -ForegroundColor White
Write-Host "  3. Cancel" -ForegroundColor White
Write-Host ""
$choice = Read-Host "Enter choice (1-3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "=== Building from Local Directory ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "This will:" -ForegroundColor Yellow
        Write-Host "  1. Build container from your local code changes" -ForegroundColor White
        Write-Host "  2. Push to OpenShift internal registry" -ForegroundColor White
        Write-Host "  3. Restart deployment with new image" -ForegroundColor White
        Write-Host ""
        
        $confirm = Read-Host "Continue? (y/n)"
        if ($confirm -ne "y") {
            Write-Host "Cancelled" -ForegroundColor Yellow
            exit 0
        }
        
        Write-Host ""
        Write-Host "Running rebuild-only.ps1..." -ForegroundColor Green
        & "$PSScriptRoot\rebuild-only.ps1"
    }
    
    "2" {
        Write-Host ""
        Write-Host "=== Building from GitHub ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "This will:" -ForegroundColor Yellow
        Write-Host "  1. Commit your changes to git" -ForegroundColor White
        Write-Host "  2. Push to GitHub" -ForegroundColor White
        Write-Host "  3. Trigger OpenShift build from GitHub" -ForegroundColor White
        Write-Host ""
        
        # Check git status
        Write-Host "Checking git status..." -ForegroundColor Yellow
        $gitStatus = git status --porcelain
        
        if ($gitStatus) {
            Write-Host ""
            Write-Host "Modified files:" -ForegroundColor Yellow
            git status --short
            Write-Host ""
            
            $commitMsg = Read-Host "Enter commit message (or press Enter to cancel)"
            if (-not $commitMsg) {
                Write-Host "Cancelled" -ForegroundColor Yellow
                exit 0
            }
            
            Write-Host ""
            Write-Host "Committing changes..." -ForegroundColor Green
            git add activation_feature_service.py
            git add *.md
            git add *.ps1
            git commit -m $commitMsg
            
            Write-Host ""
            Write-Host "Pushing to GitHub..." -ForegroundColor Green
            git push
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Error: Git push failed" -ForegroundColor Red
                exit 1
            }
            
            Write-Host ""
            Write-Host "Waiting 5 seconds for GitHub to sync..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        } else {
            Write-Host "No local changes detected. Using current GitHub state." -ForegroundColor Green
        }
        
        Write-Host ""
        Write-Host "Running deploy-from-github.ps1..." -ForegroundColor Green
        & "$PSScriptRoot\deploy-from-github.ps1"
    }
    
    "3" {
        Write-Host "Cancelled" -ForegroundColor Yellow
        exit 0
    }
    
    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Get route URL
$ROUTE_URL = oc get route rag-backend -o jsonpath='{.spec.host}' 2>$null
if ($ROUTE_URL) {
    Write-Host "Backend URL: https://$ROUTE_URL" -ForegroundColor Green
    Write-Host ""
}

Write-Host "What changed:" -ForegroundColor Yellow
Write-Host "  ✓ Improved activation feature extraction" -ForegroundColor White
Write-Host "  ✓ Cleaner, single-line descriptions" -ForegroundColor White
Write-Host "  ✓ Matches IBM Sales Manual format" -ForegroundColor White
Write-Host "  ✓ No feature code duplicates" -ForegroundColor White
Write-Host "  ✓ No table artifacts" -ForegroundColor White
Write-Host ""

Write-Host "Test the improvements:" -ForegroundColor Yellow
Write-Host "  1. Navigate to Sales Manual page in UI" -ForegroundColor White
Write-Host "  2. Select a server (e.g., E1080)" -ForegroundColor White
Write-Host "  3. Ask: 'What activations are available?'" -ForegroundColor White
Write-Host "  4. Verify descriptions are clean and concise" -ForegroundColor White
Write-Host ""

Write-Host "Monitor logs:" -ForegroundColor Yellow
Write-Host "  oc logs -f deployment/rag-backend" -ForegroundColor White
Write-Host ""

Write-Host "Run diagnostics:" -ForegroundColor Yellow
Write-Host "  .\diagnose-activation-llm.ps1" -ForegroundColor White
Write-Host ""

# Made with Bob