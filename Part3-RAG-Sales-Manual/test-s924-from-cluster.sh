#!/bin/bash
# Test S924 from inside the OpenShift cluster (like the UI does)

echo "================================================================================"
echo "  Testing S924 from Inside OpenShift Cluster"
echo "================================================================================"
echo ""

echo "[1/4] Getting a pod to exec into..."
POD=$(oc get pod -l app=carbon-rag-ui -o jsonpath='{.items[0].metadata.name}')
if [ -z "$POD" ]; then
    echo "No carbon-rag-ui pod found, trying rag-backend pod..."
    POD=$(oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
fi

if [ -z "$POD" ]; then
    echo "ERROR: No pods found to exec into"
    exit 1
fi

echo "Using pod: $POD"
echo ""

echo "[2/4] Testing backend health (internal service)..."
oc exec -it $POD -- curl -s http://rag-backend:8080/health
echo ""
echo ""

echo "[3/4] Listing collections (internal service)..."
oc exec -it $POD -- curl -s http://rag-backend:8080/api/collections | head -100
echo ""
echo ""

echo "[4/4] Testing S924 lifecycle query (internal service)..."
oc exec -it $POD -- curl -s -X POST http://rag-backend:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"question": "When did we stop supporting the S924?"}'
echo ""
echo ""

echo "================================================================================"
echo "  Analysis"
echo "================================================================================"
echo ""
echo "This tests the SAME path the UI uses (internal service name)."
echo "If this works but external route doesn't, it's a route configuration issue."
echo "If this also fails, it's a backend or data issue."
echo ""

# Made with Bob
