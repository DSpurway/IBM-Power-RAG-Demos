#!/bin/bash

################################################################################
# Script: deploy-backend-ocp.sh
# Purpose: Deploy RAG Backend to OpenShift using BuildConfig
# Usage: bash deploy-backend-ocp.sh
################################################################################

set -e

echo "🚀 Deploying RAG Backend to OpenShift..."
echo ""

# Check if logged into OpenShift
if ! oc whoami &> /dev/null; then
    echo "❌ Error: Not logged into OpenShift cluster"
    echo "Please run: oc login <cluster-url>"
    exit 1
fi

# Get current project
PROJECT=$(oc project -q)
echo "📦 Current project: $PROJECT"
echo ""

# Check if BuildConfig exists
if ! oc get bc rag-backend &> /dev/null; then
    echo "❌ Error: BuildConfig 'rag-backend' not found"
    echo "Please ensure the BuildConfig is created in your project"
    exit 1
fi

# Start new build from rag-backend directory
echo "🔨 Starting new build for rag-backend from ./rag-backend directory..."
oc start-build rag-backend --from-dir=./rag-backend --follow

echo ""
echo "✅ Build complete!"
echo ""

# Force restart deployment to pick up new image
echo "🔄 Restarting deployment to pick up new image..."
oc rollout restart deployment/rag-backend

# Wait for deployment to roll out
echo "⏳ Waiting for deployment to roll out..."
oc rollout status deployment/rag-backend --timeout=5m

echo ""
echo "✅ Deployment complete!"
echo ""

# Get service info
SERVICE_NAME=$(oc get service rag-backend-service -o jsonpath='{.metadata.name}' 2>/dev/null || echo "")

if [ -n "$SERVICE_NAME" ]; then
    echo "🌐 Backend Service: $SERVICE_NAME"
    echo ""
fi

echo "📊 To view logs:"
echo "   oc logs -f deployment/rag-backend"
echo ""
echo "🔍 To check pod status:"
echo "   oc get pods -l app=rag-backend"
echo ""
echo "🧪 To test skip logic:"
echo "   oc logs -f deployment/rag-backend | grep 'Skip Check'"
echo ""

# Made with Bob
