#!/bin/bash

# Carbon RAG UI Deployment Script for OpenShift (OCP-native)
# This script uses OpenShift's built-in build capabilities

set -e

echo "=========================================="
echo "Carbon RAG UI - OpenShift Deployment"
echo "=========================================="
echo ""

# Get current project
PROJECT=$(oc project -q)
echo "Current OpenShift project: $PROJECT"
echo ""

# Check if rag-backend is running
echo "Checking rag-backend status..."
if ! oc get deployment rag-backend &> /dev/null; then
    echo "ERROR: rag-backend deployment not found!"
    echo "Please deploy the rag-backend first."
    exit 1
fi

# Use internal service URL (no external route needed)
RAG_BACKEND_URL="http://rag-backend:8080"
echo "✓ rag-backend deployment found"
echo "  Using internal service URL: $RAG_BACKEND_URL"
echo ""

# Check if BuildConfig exists
if oc get bc carbon-rag-ui &> /dev/null; then
    echo "BuildConfig exists, starting new build..."
    oc start-build carbon-rag-ui --from-dir=. --follow
else
    echo "Creating new BuildConfig from current directory..."
    oc new-build --name=carbon-rag-ui \
        --binary=true \
        --strategy=docker \
        --to=carbon-rag-ui:latest
    
    echo "Starting initial build..."
    oc start-build carbon-rag-ui --from-dir=. --follow
fi

echo "✓ Build complete"
echo ""

# Deploy to OpenShift
echo "Applying deployment configuration..."
oc apply -f openshift-deployment.yaml

if [ $? -ne 0 ]; then
    echo "ERROR: Deployment failed!"
    exit 1
fi

echo "✓ Deployment configuration applied"
echo ""

# Wait for deployment to be ready
echo "Waiting for deployment to be ready..."
oc rollout status deployment/carbon-rag-ui --timeout=5m

if [ $? -ne 0 ]; then
    echo "WARNING: Deployment rollout timed out or failed"
    echo "Check pod status with: oc get pods -l app=carbon-rag-ui"
    echo "Check logs with: oc logs -f deployment/carbon-rag-ui"
else
    echo "✓ Deployment ready"
fi

echo ""

# Get the route
UI_ROUTE=$(oc get route carbon-rag-ui -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

if [ -n "$UI_ROUTE" ]; then
    echo "=========================================="
    echo "Deployment Complete!"
    echo "=========================================="
    echo ""
    echo "Carbon RAG UI URL: https://$UI_ROUTE"
    echo "Backend URL: $RAG_BACKEND_URL (internal)"
    echo ""
    echo "Test the deployment:"
    echo "  1. Open https://$UI_ROUTE in your browser"
    echo "  2. Navigate to the Sales Manual tab"
    echo "  3. Try querying the documentation"
    echo ""
    echo "Monitor the deployment:"
    echo "  oc get pods -l app=carbon-rag-ui"
    echo "  oc logs -f deployment/carbon-rag-ui"
    echo ""
else
    echo "WARNING: Could not get route URL"
    echo "Check route with: oc get route carbon-rag-ui"
fi

echo "Done!"

# Made with Bob