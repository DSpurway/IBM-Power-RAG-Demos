# Fresh IBM Power OCP Cluster Deployment Script (PowerShell)
# Deploys complete RAG Sales Manual demo to a new IBM Power cluster

Write-Host "=========================================="
Write-Host "IBM Power RAG Sales Manual"
Write-Host "Fresh Cluster Deployment (PowerShell)"
Write-Host "=========================================="
Write-Host ""

# Configuration
$SCRAPER_URL = "https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud"
$PROJECT_NAME = "rag-demo"

# Check prerequisites
Write-Host "Checking prerequisites..."
Write-Host ""

# Check oc CLI
try {
    $ocVersion = oc version 2>&1
    Write-Host "✅ OpenShift CLI found"
} catch {
    Write-Host "❌ Error: 'oc' CLI not found. Please install OpenShift CLI."
    exit 1
}

# Check if logged into OpenShift
try {
    $whoami = oc whoami 2>&1
    Write-Host "✅ Logged into OpenShift as: $whoami"
} catch {
    Write-Host "❌ Error: Not logged into OpenShift. Please run 'oc login' first."
    exit 1
}

Write-Host ""

# Get current project
$currentProject = oc project -q 2>$null
Write-Host "Current project: $currentProject"
Write-Host ""

# Create or switch to project
Write-Host "Setting up project: $PROJECT_NAME"
$projectExists = oc get project $PROJECT_NAME 2>$null
if ($projectExists) {
    Write-Host "Project $PROJECT_NAME exists, switching to it..."
    oc project $PROJECT_NAME
} else {
    Write-Host "Creating project $PROJECT_NAME..."
    oc new-project $PROJECT_NAME
}

Write-Host ""

# Confirm deployment
Write-Host "=========================================="
Write-Host "Ready to Deploy"
Write-Host "=========================================="
Write-Host ""
Write-Host "Project: $PROJECT_NAME"
Write-Host "Scraper: $SCRAPER_URL"
Write-Host ""
Write-Host "Services to deploy:"
Write-Host "  1. OpenSearch (Vector Database)"
Write-Host "  2. Granite LLM Service (Part 3)"
Write-Host "  3. TinyLlama LLM Service (Part 1 & 2)"
Write-Host "  4. RAG Backend (Consolidated)"
Write-Host "  5. Carbon RAG UI (Frontend)"
Write-Host ""
$confirm = Read-Host "Continue with deployment? (y/n)"

if ($confirm -ne "y") {
    Write-Host "Deployment cancelled"
    exit 0
}

Write-Host ""

# Step 1: Deploy OpenSearch
Write-Host "=========================================="
Write-Host "Step 1/5: Deploying OpenSearch"
Write-Host "=========================================="
Write-Host ""

Set-Location opensearch-deployment

oc apply -f opensearch-deploy.yaml
oc apply -f opensearch-svc.yaml
# No route needed - OpenSearch is accessed internally by rag-backend

Write-Host "Waiting for OpenSearch to be ready..."
oc rollout status deployment/opensearch-service --timeout=10m

Write-Host "✅ OpenSearch deployed"
Write-Host ""

# Step 2: Deploy Granite LLM
Write-Host "=========================================="
Write-Host "Step 2/5: Deploying Granite LLM Service"
Write-Host "=========================================="
Write-Host ""

Set-Location ..\granite-service

# Create build if it doesn't exist
$buildExists = oc get bc/granite-service 2>$null
if (-not $buildExists) {
    oc new-build --name=granite-service --binary --strategy=docker
}

Write-Host "Starting build (this may take 5-10 minutes)..."
oc start-build granite-service --from-dir=. --follow

oc apply -f granite-deploy.yaml
oc apply -f granite-svc.yaml
oc apply -f granite-route.yaml

Write-Host "Waiting for Granite service to be ready (this may take 5-10 minutes)..."
oc rollout status deployment/granite-service --timeout=15m

Write-Host "✅ Granite LLM deployed"
Write-Host ""

# Step 3: Deploy TinyLlama
Write-Host "=========================================="
Write-Host "Step 3/5: Deploying TinyLlama LLM Service"
Write-Host "=========================================="
Write-Host ""

Set-Location ..\llama-cpp-server

# Create build if it doesn't exist
$buildExists = oc get bc/llama-service 2>$null
if (-not $buildExists) {
    oc new-build --name=llama-service --binary --strategy=docker
}

Write-Host "Starting build..."
oc start-build llama-service --from-dir=. --follow

oc apply -f llama-deploy.yaml
oc apply -f llama-svc.yaml
oc apply -f llama-route.yaml

Write-Host "Waiting for TinyLlama service to be ready..."
oc rollout status deployment/llama-service --timeout=10m

Write-Host "✅ TinyLlama LLM deployed"
Write-Host ""

# Step 4: Deploy RAG Backend
Write-Host "=========================================="
Write-Host "Step 4/5: Deploying RAG Backend"
Write-Host "=========================================="
Write-Host ""

Set-Location ..\rag-backend

# Create build if it doesn't exist
$buildExists = oc get bc/rag-backend 2>$null
if (-not $buildExists) {
    oc new-build --name=rag-backend --binary --strategy=docker
}

Write-Host "Starting build..."
oc start-build rag-backend --from-dir=. --follow

# Apply deployment if it doesn't exist
$deployExists = oc get deployment/rag-backend 2>$null
if (-not $deployExists) {
    oc apply -f rag-backend-deploy.yaml
}

# Create service and route if they don't exist
$svcExists = oc get svc/rag-backend 2>$null
if (-not $svcExists) {
    oc apply -f rag-backend-svc.yaml
}

$routeExists = oc get route/rag-backend 2>$null
if (-not $routeExists) {
    oc apply -f rag-backend-route.yaml
}

# Set environment variables
Write-Host "Configuring backend environment variables..."
oc set env deployment/rag-backend `
  OPENSEARCH_HOST=opensearch-service `
  OPENSEARCH_PORT=9200 `
  GRANITE_HOST=granite-service `
  GRANITE_PORT=8080 `
  TINYLLAMA_HOST=llama-service `
  TINYLLAMA_PORT=8080 `
  SCRAPER_URL=$SCRAPER_URL `
  CORS_ORIGIN='*'

Write-Host "Waiting for backend to be ready..."
oc rollout status deployment/rag-backend --timeout=10m

Write-Host "✅ RAG Backend deployed"
Write-Host ""

# Step 5: Deploy Carbon RAG UI
Write-Host "=========================================="
Write-Host "Step 5/5: Deploying Carbon RAG UI"
Write-Host "=========================================="
Write-Host ""

Set-Location ..\carbon-rag-ui

# Create build if it doesn't exist
$buildExists = oc get bc/carbon-rag-ui 2>$null
if (-not $buildExists) {
    oc new-build --name=carbon-rag-ui --binary --strategy=docker
}

Write-Host "Starting build..."
oc start-build carbon-rag-ui --from-dir=. --follow

# Apply deployment if it doesn't exist
$deployExists = oc get deployment/carbon-rag-ui 2>$null
if (-not $deployExists) {
    oc apply -f carbon-rag-ui-deploy.yaml
}

# Create service and route if they don't exist
$svcExists = oc get svc/carbon-rag-ui 2>$null
if (-not $svcExists) {
    oc apply -f carbon-rag-ui-svc.yaml
}

$routeExists = oc get route/carbon-rag-ui 2>$null
if (-not $routeExists) {
    oc apply -f carbon-rag-ui-route.yaml
}

# Set environment variables
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
Write-Host "Configuring frontend environment variables..."
oc set env deployment/carbon-rag-ui `
  NEXT_PUBLIC_API_URL=https://$BACKEND_URL

Write-Host "Waiting for frontend to be ready..."
oc rollout status deployment/carbon-rag-ui --timeout=10m

Write-Host "✅ Carbon RAG UI deployed"
Write-Host ""

# Verification
Write-Host "=========================================="
Write-Host "Deployment Complete!"
Write-Host "=========================================="
Write-Host ""

Write-Host "Verifying deployments..."
Write-Host ""

# Get all service URLs
$OPENSEARCH_URL = oc get route opensearch-service -o jsonpath='{.spec.host}' 2>$null
if (-not $OPENSEARCH_URL) { $OPENSEARCH_URL = "N/A" }

$GRANITE_URL = oc get route granite-service -o jsonpath='{.spec.host}' 2>$null
if (-not $GRANITE_URL) { $GRANITE_URL = "N/A" }

$LLAMA_URL = oc get route llama-service -o jsonpath='{.spec.host}' 2>$null
if (-not $LLAMA_URL) { $LLAMA_URL = "N/A" }

$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}' 2>$null
if (-not $BACKEND_URL) { $BACKEND_URL = "N/A" }

$UI_URL = oc get route carbon-rag-ui -o jsonpath='{.spec.host}' 2>$null
if (-not $UI_URL) { $UI_URL = "N/A" }

Write-Host "Service URLs:"
Write-Host "  OpenSearch:    https://$OPENSEARCH_URL"
Write-Host "  Granite LLM:   https://$GRANITE_URL"
Write-Host "  TinyLlama LLM: https://$LLAMA_URL"
Write-Host "  RAG Backend:   https://$BACKEND_URL"
Write-Host "  Carbon UI:     https://$UI_URL"
Write-Host "  Scraper:       $SCRAPER_URL"
Write-Host ""

Write-Host "Pod Status:"
oc get pods
Write-Host ""

Write-Host "=========================================="
Write-Host "Next Steps"
Write-Host "=========================================="
Write-Host ""
Write-Host "1. Open the UI in your browser:"
Write-Host "   https://$UI_URL"
Write-Host ""
Write-Host "2. Navigate to the Sales Manual page"
Write-Host ""
Write-Host "3. Click 'Load All Documents' to ingest all 26 servers"
Write-Host "   - First run: ~45-60 minutes (full ingestion)"
Write-Host "   - Subsequent runs: ~5-10 minutes (skip logic)"
Write-Host ""
Write-Host "4. Test queries against the indexed servers"
Write-Host ""
Write-Host "To monitor backend logs:"
Write-Host "  oc logs -f deployment/rag-backend"
Write-Host ""
Write-Host "To check bulk ingestion status:"
Write-Host "  curl.exe https://$BACKEND_URL/api/bulk-ingestion-status"
Write-Host ""
Write-Host "For troubleshooting, see DEPLOY_FRESH_POWER_CLUSTER.md"
Write-Host ""

# Return to original directory
Set-Location ..

Write-Host "Deployment script complete!"

# Made with Bob
