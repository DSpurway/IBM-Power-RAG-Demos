#!/bin/bash

# Fresh OpenShift Cluster Deployment Script
# Deploys complete RAG Sales Manual demo to a new cluster

set -e

echo "=========================================="
echo "IBM Power RAG Sales Manual"
echo "Fresh Cluster Deployment"
echo "=========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check oc CLI
if ! command -v oc &> /dev/null; then
    echo "❌ Error: 'oc' CLI not found. Please install OpenShift CLI."
    exit 1
fi

# Check if logged into OpenShift
if ! oc whoami &> /dev/null; then
    echo "❌ Error: Not logged into OpenShift. Please run 'oc login' first."
    exit 1
fi

echo "✅ OpenShift CLI found and logged in"
echo ""

# Get current project
CURRENT_PROJECT=$(oc project -q 2>/dev/null || echo "")
echo "Current project: $CURRENT_PROJECT"
echo ""

# Prompt for project name
read -p "Enter project name (default: rag-demo): " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-rag-demo}

# Create or switch to project
if oc get project "$PROJECT_NAME" &> /dev/null; then
    echo "Project $PROJECT_NAME exists, switching to it..."
    oc project "$PROJECT_NAME"
else
    echo "Creating project $PROJECT_NAME..."
    oc new-project "$PROJECT_NAME"
fi

echo ""

# Get scraper URL
echo "=========================================="
echo "Scraper Service Configuration"
echo "=========================================="
echo ""
echo "The scraper service is deployed on IBM Code Engine (external to cluster)."
echo "It won't expire when the cluster expires."
echo ""
read -p "Enter scraper URL (e.g., https://scraper.xxx.code-engine.appdomain.cloud): " SCRAPER_URL

if [ -z "$SCRAPER_URL" ]; then
    echo "❌ Error: Scraper URL is required"
    exit 1
fi

echo ""
echo "Using scraper URL: $SCRAPER_URL"
echo ""

# Deployment confirmation
echo "=========================================="
echo "Ready to Deploy"
echo "=========================================="
echo ""
echo "Project: $PROJECT_NAME"
echo "Scraper: $SCRAPER_URL"
echo ""
echo "Services to deploy:"
echo "  1. OpenSearch (Vector Database)"
echo "  2. Granite LLM Service (Part 3)"
echo "  3. TinyLlama LLM Service (Part 1 & 2)"
echo "  4. RAG Backend (Consolidated)"
echo "  5. Carbon RAG UI (Frontend)"
echo ""
read -p "Continue with deployment? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""

# Step 1: Deploy OpenSearch
echo "=========================================="
echo "Step 1/5: Deploying OpenSearch"
echo "=========================================="
echo ""

cd opensearch-deployment

oc apply -f opensearch-deploy.yaml
oc apply -f opensearch-svc.yaml
oc apply -f opensearch-route.yaml

echo "Waiting for OpenSearch to be ready..."
oc rollout status deployment/opensearch-service --timeout=10m

echo "✅ OpenSearch deployed"
echo ""

# Step 2: Deploy Granite LLM
echo "=========================================="
echo "Step 2/5: Deploying Granite LLM Service"
echo "=========================================="
echo ""

cd ../granite-service

# Create build if it doesn't exist
if ! oc get bc/granite-service &> /dev/null; then
    oc new-build --name=granite-service --binary --strategy=docker
fi

oc start-build granite-service --from-dir=. --follow

oc apply -f granite-deploy.yaml
oc apply -f granite-svc.yaml
oc apply -f granite-route.yaml

echo "Waiting for Granite service to be ready (this may take 5-10 minutes)..."
oc rollout status deployment/granite-service --timeout=15m

echo "✅ Granite LLM deployed"
echo ""

# Step 3: Deploy TinyLlama
echo "=========================================="
echo "Step 3/5: Deploying TinyLlama LLM Service"
echo "=========================================="
echo ""

cd ../llama-cpp-server

# Create build if it doesn't exist
if ! oc get bc/llama-service &> /dev/null; then
    oc new-build --name=llama-service --binary --strategy=docker
fi

oc start-build llama-service --from-dir=. --follow

oc apply -f llama-deploy.yaml
oc apply -f llama-svc.yaml
oc apply -f llama-route.yaml

echo "Waiting for TinyLlama service to be ready..."
oc rollout status deployment/llama-service --timeout=10m

echo "✅ TinyLlama LLM deployed"
echo ""

# Step 4: Deploy RAG Backend
echo "=========================================="
echo "Step 4/5: Deploying RAG Backend"
echo "=========================================="
echo ""

cd ../rag-backend

# Create build if it doesn't exist
if ! oc get bc/rag-backend &> /dev/null; then
    oc new-build --name=rag-backend --binary --strategy=docker
fi

oc start-build rag-backend --from-dir=. --follow

# Apply deployment if it doesn't exist
if ! oc get deployment/rag-backend &> /dev/null; then
    oc apply -f rag-backend-deploy.yaml
fi

# Create service and route if they don't exist
if ! oc get svc/rag-backend &> /dev/null; then
    oc apply -f rag-backend-svc.yaml
fi

if ! oc get route/rag-backend &> /dev/null; then
    oc apply -f rag-backend-route.yaml
fi

# Set environment variables
echo "Configuring backend environment variables..."
oc set env deployment/rag-backend \
  OPENSEARCH_HOST=opensearch-service \
  OPENSEARCH_PORT=9200 \
  GRANITE_HOST=granite-service \
  GRANITE_PORT=8080 \
  TINYLLAMA_HOST=llama-service \
  TINYLLAMA_PORT=8080 \
  SCRAPER_URL=$SCRAPER_URL \
  CORS_ORIGIN='*'

echo "Waiting for backend to be ready..."
oc rollout status deployment/rag-backend --timeout=10m

echo "✅ RAG Backend deployed"
echo ""

# Step 5: Deploy Carbon RAG UI
echo "=========================================="
echo "Step 5/5: Deploying Carbon RAG UI"
echo "=========================================="
echo ""

cd ../carbon-rag-ui

# Create build if it doesn't exist
if ! oc get bc/carbon-rag-ui &> /dev/null; then
    oc new-build --name=carbon-rag-ui --binary --strategy=docker
fi

oc start-build carbon-rag-ui --from-dir=. --follow

# Apply deployment if it doesn't exist
if ! oc get deployment/carbon-rag-ui &> /dev/null; then
    oc apply -f carbon-rag-ui-deploy.yaml
fi

# Create service and route if they don't exist
if ! oc get svc/carbon-rag-ui &> /dev/null; then
    oc apply -f carbon-rag-ui-svc.yaml
fi

if ! oc get route/carbon-rag-ui &> /dev/null; then
    oc apply -f carbon-rag-ui-route.yaml
fi

# Set environment variables
BACKEND_URL=$(oc get route rag-backend -o jsonpath='{.spec.host}')
echo "Configuring frontend environment variables..."
oc set env deployment/carbon-rag-ui \
  NEXT_PUBLIC_API_URL=https://$BACKEND_URL

echo "Waiting for frontend to be ready..."
oc rollout status deployment/carbon-rag-ui --timeout=10m

echo "✅ Carbon RAG UI deployed"
echo ""

# Verification
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""

echo "Verifying deployments..."
echo ""

# Get all service URLs
OPENSEARCH_URL=$(oc get route opensearch-service -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")
GRANITE_URL=$(oc get route granite-service -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")
LLAMA_URL=$(oc get route llama-service -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")
BACKEND_URL=$(oc get route rag-backend -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")
UI_URL=$(oc get route carbon-rag-ui -o jsonpath='{.spec.host}' 2>/dev/null || echo "N/A")

echo "Service URLs:"
echo "  OpenSearch:    https://$OPENSEARCH_URL"
echo "  Granite LLM:   https://$GRANITE_URL"
echo "  TinyLlama LLM: https://$LLAMA_URL"
echo "  RAG Backend:   https://$BACKEND_URL"
echo "  Carbon UI:     https://$UI_URL"
echo "  Scraper:       $SCRAPER_URL"
echo ""

echo "Pod Status:"
oc get pods
echo ""

echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Open the UI in your browser:"
echo "   https://$UI_URL"
echo ""
echo "2. Navigate to the Sales Manual page"
echo ""
echo "3. Click 'Load All Documents' to ingest all 26 servers"
echo "   - First run: ~45-60 minutes (full ingestion)"
echo "   - Subsequent runs: ~5-10 minutes (skip logic)"
echo ""
echo "4. Test queries against the indexed servers"
echo ""
echo "To monitor backend logs:"
echo "  oc logs -f deployment/rag-backend"
echo ""
echo "To check bulk ingestion status:"
echo "  curl https://$BACKEND_URL/api/bulk-ingestion-status | jq"
echo ""
echo "For troubleshooting, see FRESH_CLUSTER_DEPLOYMENT.md"
echo ""

# Made with Bob
