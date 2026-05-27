#!/bin/bash
# Check actual image SHAs

echo "====================================="
echo "  Image SHA Comparison"
echo "====================================="
echo ""

echo "Pod's image SHA:"
POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
oc get pod $POD -o jsonpath='{.status.containerStatuses[0].imageID}'
echo ""
echo ""

echo "Latest build's output image:"
oc get build -l buildconfig=rag-backend --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].status.output.to.imageDigest}'
echo ""
echo ""

echo "ImageStream latest tag SHA:"
oc get is rag-backend -o jsonpath='{.status.tags[?(@.tag=="latest")].items[0].image}'
echo ""
echo ""

echo "Force pull latest image:"
echo "oc delete pod $POD"
echo ""

echo "====================================="

# Made with Bob
