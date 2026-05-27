#!/bin/bash
# Check what image the deployment is actually using

echo "====================================="
echo "  Deployment Image Check"
echo "====================================="
echo ""

echo "Current deployment image:"
oc get deployment rag-backend -o jsonpath='{.spec.template.spec.containers[0].image}'
echo ""
echo ""

echo "Latest build image:"
oc get build -l buildconfig=rag-backend --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].status.outputDockerImageReference}'
echo ""
echo ""

echo "Image stream tags:"
oc get is rag-backend -o jsonpath='{.status.tags[*].tag}'
echo ""
echo ""

echo "====================================="

# Made with Bob
