#!/bin/bash
# Compare what UI sees vs what backend reports

echo "================================================================================"
echo "  UI vs Backend Data Comparison"
echo "================================================================================"
echo ""

POD=$(oc get pod -l app=carbon-rag-ui -o jsonpath='{.items[0].metadata.name}')

echo "Testing from UI pod (same as browser)..."
echo ""

echo "[1/2] What the UI's Next.js API proxy returns..."
oc exec $POD -- curl -s http://localhost:3000/api/rag/collections | python -m json.tool | grep -A 5 "9009-42"
echo ""
echo ""

echo "[2/2] What the backend directly returns..."
oc exec $POD -- curl -s http://rag-backend:8080/api/collections | python -m json.tool | grep -A 5 "9009-42"
echo ""
echo ""

echo "================================================================================"
echo "  Summary"
echo "================================================================================"
echo ""
echo "From backend API (earlier test):"
echo "  9009-42A: NOT FOUND"
echo "  9009-42G: 3613 documents"
echo ""
echo "From UI screenshot:"
echo "  9009-42A: 4430 documents (INCORRECT - cached?)"
echo "  9009-42G: 4597 documents (doesn't match 3613!)"
echo ""
echo "The UI document counts don't match backend reality."
echo "This suggests the UI is showing stale cached data."
echo ""
echo "Solution: Hard refresh the UI (Ctrl+Shift+R) and check again."
echo ""

# Made with Bob
