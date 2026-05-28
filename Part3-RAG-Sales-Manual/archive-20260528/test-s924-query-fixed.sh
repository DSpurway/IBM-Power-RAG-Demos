#!/bin/bash
# Test S924 query with correct JSON format

echo "================================================================================"
echo "  Testing S924 Query - Fixed JSON"
echo "================================================================================"
echo ""

POD=$(oc get pod -l app=carbon-rag-ui -o jsonpath='{.items[0].metadata.name}')
if [ -z "$POD" ]; then
    POD=$(oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
fi

echo "Using pod: $POD"
echo ""

echo "[1/2] Testing S924 query with 'prompt' parameter..."
oc exec $POD -- curl -s -X POST http://rag-backend:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "When did we stop supporting the S924?"}'
echo ""
echo ""

echo "[2/2] Testing S924 query with 'question' parameter..."
oc exec $POD -- curl -s -X POST http://rag-backend:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"question": "When did we stop supporting the S924?"}'
echo ""
echo ""

echo "================================================================================"
echo "  Key Finding from Collections List"
echo "================================================================================"
echo ""
echo "MTM 9009-42A (S924) is NOT in the collections list!"
echo "MTM 9009-42G (S924-G) IS in the list with 3613 documents"
echo ""
echo "But your UI shows S924 (9009-42A) with 4430 documents."
echo "This suggests the UI might be caching old data or showing incorrect status."
echo ""

# Made with Bob
