#!/bin/bash
# Test S924 query using the same path as the UI

BACKEND_URL="https://rag-backend-llm-on-techzone.apps.p1219.cecc.ihost.com"

echo "================================================================================"
echo "  Testing S924 Query - Direct to Backend"
echo "================================================================================"
echo ""

echo "Query: 'When did we stop supporting the S924?'"
echo ""

echo "[1/2] Testing with automatic collection detection (like UI does)..."
curl -s -X POST "${BACKEND_URL}/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "When did we stop supporting the S924?"
  }' | python -m json.tool

echo ""
echo ""

echo "[2/2] Testing with explicit MTM 9009-42A..."
curl -s -X POST "${BACKEND_URL}/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "When did we stop supporting the S924?",
    "server_mtm": "9009-42A"
  }' | python -m json.tool

echo ""
echo "================================================================================"
echo "  Analysis"
echo "================================================================================"
echo ""
echo "The UI shows S924 (9009-42A) as 'Indexed' with 4430 documents."
echo "If the query fails, the issue is in the query routing or table lookup logic."
echo ""

# Made with Bob
