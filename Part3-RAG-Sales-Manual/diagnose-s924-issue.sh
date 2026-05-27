#!/bin/bash
# Diagnose S924 ingestion issue

BACKEND_URL="https://rag-backend-llm-on-techzone.apps.p1219.cecc.ihost.com"

echo "================================================================================"
echo "  S924 Ingestion Diagnostic"
echo "================================================================================"
echo ""

echo "[1/4] Checking backend health..."
curl -s "${BACKEND_URL}/health"
echo ""
echo ""

echo "[2/4] Listing all indexed MTMs..."
echo "Looking for MTM 9009-42A (S924) and 9009-42G (S924-G)..."
curl -s "${BACKEND_URL}/api/collections" > /tmp/collections.json
cat /tmp/collections.json
echo ""
echo ""

echo "[3/4] Checking if S924 MTMs are in the list..."
if grep -q "9009-42A" /tmp/collections.json; then
    echo "✓ Found MTM 9009-42A in collections"
else
    echo "✗ MTM 9009-42A NOT FOUND - needs to be ingested"
fi

if grep -q "9009-42G" /tmp/collections.json; then
    echo "✓ Found MTM 9009-42G in collections"
else
    echo "✗ MTM 9009-42G NOT FOUND - needs to be ingested"
fi
echo ""

echo "[4/4] Testing a query for S924..."
curl -s -X POST "${BACKEND_URL}/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"question": "When did we stop supporting the S924?"}' > /tmp/query_result.json
cat /tmp/query_result.json
echo ""
echo ""

echo "================================================================================"
echo "  Diagnostic Summary"
echo "================================================================================"
echo ""
echo "If MTM 9009-42A is NOT in the collections list, you need to:"
echo "  1. Re-run the ingestion for S924"
echo "  2. Use the command:"
echo "     python windows_scraper.py \\"
echo "       'https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42a' \\"
echo "       --backend ${BACKEND_URL} \\"
echo "       --server-model S924"
echo ""

# Made with Bob
