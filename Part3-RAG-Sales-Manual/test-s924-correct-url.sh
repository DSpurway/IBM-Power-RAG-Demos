#!/bin/bash
# Test S924 query with CORRECT backend URL

# CORRECT URL from OpenShift route
BACKEND_URL="https://rag-backend-llm-on-techzone.apps.p1265.cecc.ihost.com"

echo "================================================================================"
echo "  Testing S924 Query - CORRECT Backend URL"
echo "================================================================================"
echo ""
echo "Using: ${BACKEND_URL}"
echo ""

echo "[1/3] Testing /health endpoint..."
curl -s "${BACKEND_URL}/health"
echo ""
echo ""

echo "[2/3] Listing collections..."
curl -s "${BACKEND_URL}/api/collections" | python -m json.tool | head -50
echo ""
echo ""

echo "[3/3] Testing S924 lifecycle query..."
curl -s -X POST "${BACKEND_URL}/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "When did we stop supporting the S924?"
  }' | python -m json.tool

echo ""
echo "================================================================================"
echo "  Done"
echo "================================================================================"

# Made with Bob
