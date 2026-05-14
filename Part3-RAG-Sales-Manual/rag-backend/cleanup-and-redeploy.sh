#!/bin/bash
# Cleanup old rag-backend-opensearch resources and redeploy with correct name
# This script removes the incorrectly named resources and deploys fresh with "rag-backend"

set -e

echo "=========================================="
echo "Cleanup and Redeploy RAG Backend"
echo "=========================================="

# Check if logged into OpenShift
if ! oc whoami &> /dev/null; then
    echo "Error: Not logged into OpenShift. Please run 'oc login' first."
    exit 1
fi

PROJECT=$(oc project -q)
echo "Working in project: $PROJECT"

echo ""
echo "=========================================="
echo "Step 1: Cleaning up old resources..."
echo "=========================================="

# Delete old resources with wrong name
OLD_RESOURCES=(
    "buildconfig/rag-backend-opensearch"
    "imagestream/rag-backend-opensearch"
    "deployment/rag-backend-opensearch"
    "service/rag-backend-opensearch"
    "route/rag-backend-opensearch"
)

for resource in "${OLD_RESOURCES[@]}"; do
    echo "Checking for $resource..."
    if oc get $resource &> /dev/null; then
        echo "  Deleting $resource"
        oc delete $resource --ignore-not-found=true
    else
        echo "  Not found (OK)"
    fi
done

echo ""
echo "=========================================="
echo "Step 2: Deploying with correct name..."
echo "=========================================="

# Run the corrected deployment script
echo ""
echo "Running deploy.sh..."
bash "$(dirname "$0")/deploy.sh"

echo ""
echo "=========================================="
echo "Cleanup and Redeploy Complete!"
echo "=========================================="
echo ""
echo "New resources created with name: rag-backend"
echo ""
echo "To check status:"
echo "  oc get all -l app=rag-backend"
echo ""
echo "To view logs:"
echo "  oc logs -f deployment/rag-backend"
echo ""
echo "To get route URL:"
echo "  oc get route rag-backend"

# Made with Bob
