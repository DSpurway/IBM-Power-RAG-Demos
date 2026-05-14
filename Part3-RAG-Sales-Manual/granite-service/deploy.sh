#!/bin/bash

# Granite Service Deployment Script for OpenShift
# This deploys the Granite 4.0 Micro model for complex RAG queries

set -e

echo "=========================================="
echo "Granite Service Deployment"
echo "=========================================="
echo ""

# Get the current project
PROJECT=$(oc project -q)
echo "Current project: $PROJECT"
echo ""

# Check if we're in the right directory
if [ ! -f "Dockerfile" ]; then
    echo "Error: Dockerfile not found. Please run this script from the granite-service directory."
    exit 1
fi

# Build the container image
echo "Step 1: Building Granite service container image..."
echo "This will take several minutes as it downloads the Granite 4.0 Micro model (~2.5GB)"
oc new-build --name=granite-service --binary --strategy=docker || echo "Build config already exists"
oc start-build granite-service --from-dir=. --follow --wait

echo ""
echo "Step 2: Deploying Granite service..."
oc apply -f granite-deploy.yaml

echo ""
echo "Step 3: Creating service..."
oc apply -f granite-svc.yaml

echo ""
echo "Step 4: Creating route..."
oc apply -f granite-route.yaml

echo ""
echo "Step 5: Waiting for deployment to be ready..."
oc rollout status deployment/granite-service --timeout=10m

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""

# Get the route URL
ROUTE_URL=$(oc get route granite-service -o jsonpath='{.spec.host}')
echo "Granite service is available at: https://$ROUTE_URL"
echo ""
echo "Test the service with:"
echo "  curl https://$ROUTE_URL/health"
echo ""
echo "The RAG backend will automatically use this service for complex queries."
echo "Make sure to set GRANITE_HOST=granite-service in the rag-backend deployment."
echo ""

# Made with Bob
