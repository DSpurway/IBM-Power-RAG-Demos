#!/bin/bash

echo "=========================================="
echo "Fixing Carbon RAG UI Deployment"
echo "=========================================="
echo ""

NAMESPACE=$(oc project -q)
echo "Current namespace: $NAMESPACE"
echo ""

echo "Step 1: Updating deployment to use internal backend service..."
echo "Setting RAG_BACKEND_URL to internal service: http://rag-backend:8080"

# Update the deployment to use internal service name
oc set env deployment/carbon-rag-ui \
  RAG_BACKEND_URL=http://rag-backend:8080 \
  -n $NAMESPACE

echo ""
echo "Step 2: Removing unnecessary backend route..."
oc delete route rag-backend -n $NAMESPACE --ignore-not-found=true

echo ""
echo "Step 3: Waiting for deployment to restart..."
oc rollout status deployment/carbon-rag-ui --timeout=3m -n $NAMESPACE

echo ""
echo "=========================================="
echo "Configuration Complete"
echo "=========================================="
echo ""

# Display current routes
echo "Current routes (should only show carbon-rag-ui):"
oc get routes -n $NAMESPACE

echo ""
echo "=========================================="
echo "Frontend URL"
echo "=========================================="
UI_URL=$(oc get route carbon-rag-ui -n $NAMESPACE -o jsonpath='{.spec.host}')
echo "Carbon RAG UI: https://$UI_URL"
echo ""
echo "The frontend now uses internal service communication:"
echo "  Frontend -> http://rag-backend:8080 (internal)"
echo ""

# Check pod status
echo "Pod status:"
oc get pods -l app=carbon-rag-ui -n $NAMESPACE

echo ""
echo "Checking deployment environment variables:"
oc set env deployment/carbon-rag-ui --list -n $NAMESPACE | grep RAG_BACKEND_URL

# Made with Bob
