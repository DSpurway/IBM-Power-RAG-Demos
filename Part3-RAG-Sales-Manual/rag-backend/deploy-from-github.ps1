#!/usr/bin/env pwsh
# Deploy RAG Backend from GitHub
# This ensures we're using the latest committed code

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "RAG Backend Deployment from GitHub" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Configuration
$PROJECT = "llm-on-techzone"
$APP_NAME = "rag-backend"
$GITHUB_REPO = "https://github.com/DSpurway/IBM-Power-RAG-Demos.git"
$CONTEXT_DIR = "Part3-RAG-Sales-Manual/rag-backend"
$BRANCH = "main"

Write-Host "Deploying to project: $PROJECT" -ForegroundColor Yellow

# Delete existing resources to force fresh build
Write-Host "`nStep 1: Cleaning up existing resources..." -ForegroundColor Green
oc delete bc/$APP_NAME -n $PROJECT --ignore-not-found=true
oc delete is/$APP_NAME -n $PROJECT --ignore-not-found=true
oc delete deployment/$APP_NAME -n $PROJECT --ignore-not-found=true
oc delete svc/$APP_NAME -n $PROJECT --ignore-not-found=true
oc delete route/$APP_NAME -n $PROJECT --ignore-not-found=true

Write-Host "`nStep 2: Creating new app from GitHub..." -ForegroundColor Green
oc new-app $GITHUB_REPO `
    --context-dir=$CONTEXT_DIR `
    --name=$APP_NAME `
    --strategy=docker `
    -n $PROJECT

Write-Host "`nStep 3: Exposing service..." -ForegroundColor Green
oc expose svc/$APP_NAME -n $PROJECT

Write-Host "`nStep 4: Waiting for build to complete..." -ForegroundColor Green
oc logs -f bc/$APP_NAME -n $PROJECT

Write-Host "`nStep 5: Applying Watson Assistant credentials..." -ForegroundColor Green
# Use oc patch with proper JSON to set environment variables from secret
oc patch deployment/$APP_NAME -n $PROJECT --type=json -p='[
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"WATSON_ASSISTANT_API_KEY","valueFrom":{"secretKeyRef":{"name":"watson-assistant-credentials","key":"api-key"}}}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"WATSON_ASSISTANT_URL","valueFrom":{"secretKeyRef":{"name":"watson-assistant-credentials","key":"url"}}}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"WATSON_ASSISTANT_ID","valueFrom":{"secretKeyRef":{"name":"watson-assistant-credentials","key":"assistant-id"}}}}
]'

Write-Host "Watson Assistant credentials applied from secret" -ForegroundColor Green

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`nGetting route URL..." -ForegroundColor Green
$ROUTE_URL = oc get route $APP_NAME -n $PROJECT -o jsonpath='{.spec.host}'
Write-Host "`nRAG Backend URL: https://$ROUTE_URL" -ForegroundColor Yellow

Write-Host "`nTest the service:" -ForegroundColor Green
Write-Host "  curl https://$ROUTE_URL/health" -ForegroundColor White

# Made with Bob
