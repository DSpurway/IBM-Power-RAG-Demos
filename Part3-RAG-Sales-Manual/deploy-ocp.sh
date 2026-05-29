#!/bin/bash

################################################################################
# Script: deploy-ocp.sh
# Purpose: Deploy Carbon RAG UI to OpenShift using BuildConfig
# Usage: bash deploy-ocp.sh
################################################################################

set -e

echo "🚀 Deploying Carbon RAG UI to OpenShift..."
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
if ! oc get bc carbon-rag-ui &> /dev/null; then
    echo "❌ Error: BuildConfig 'carbon-rag-ui' not found"
    echo "Please ensure the BuildConfig is created in your project"
    exit 1
fi

# Start new build from carbon-rag-ui directory
echo "🔨 Starting new build for carbon-rag-ui from ./carbon-rag-ui directory..."
oc start-build carbon-rag-ui --from-dir=./carbon-rag-ui --follow

echo ""
echo "✅ Build complete!"
echo ""

# Force restart deployment to pick up new image
echo "🔄 Restarting deployment to pick up new image..."
oc rollout restart deployment/carbon-rag-ui

# Wait for deployment to roll out
echo "⏳ Waiting for deployment to roll out..."
oc rollout status deployment/carbon-rag-ui --timeout=5m

echo ""
echo "✅ Deployment complete!"
echo ""

# Get route URL
ROUTE_URL=$(oc get route carbon-rag-ui -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

if [ -n "$ROUTE_URL" ]; then
    echo "🌐 Application URL: https://$ROUTE_URL"
else
    echo "⚠️  No route found. Create one with:"
    echo "   oc expose service carbon-rag-ui"
fi

echo ""
echo "📊 To view logs:"
echo "   oc logs -f deployment/carbon-rag-ui"
echo ""
echo "🔍 To check pod status:"
echo "   oc get pods -l app=carbon-rag-ui"
echo ""

# Made with Bob
