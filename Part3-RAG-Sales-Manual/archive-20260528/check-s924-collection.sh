#!/bin/bash
# Check if S924 collection exists and has data

BACKEND_URL="https://rag-backend-llm-on-techzone.apps.p1219.cecc.ihost.com"

echo "================================================================================"
echo "  Checking S924 Collection Status"
echo "================================================================================"
echo ""

echo "[1/3] Listing all collections..."
curl -s "${BACKEND_URL}/api/collections" | python -m json.tool
echo ""

echo "[2/3] Checking for S924-specific collections..."
echo "Expected collection names:"
echo "  - rag_mtm_9009_42a (for MTM 9009-42A)"
echo "  - rag_mtm_9009_42g (for MTM 9009-42G)"
echo ""

echo "[3/3] Testing S924 lifecycle query..."
curl -s -X POST "${BACKEND_URL}/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "When did we stop supporting the S924?",
    "collection_name": "rag_mtm_9009_42a"
  }' | python -m json.tool

echo ""
echo "================================================================================"
echo "  Check Complete"
echo "================================================================================"

# Made with Bob
