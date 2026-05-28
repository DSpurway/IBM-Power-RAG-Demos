#!/bin/bash
# Test the intelligent skip logic (Windows compatible - no jq needed)

echo "=== Testing Intelligent Skip Logic ==="
echo ""
echo "This will trigger bulk ingestion and show skip behavior"
echo ""

BACKEND_URL="https://rag-backend-rag-demo.apps.p1265.cecc.ihost.com"

echo "1. Starting bulk ingestion (intelligent skip enabled by default)..."
curl -X POST "${BACKEND_URL}/api/start-bulk-ingestion" \
  -H "Content-Type: application/json" \
  -s

echo ""
echo ""
echo "2. Waiting 5 seconds for processing to start..."
sleep 5

echo ""
echo "3. Checking status (should show skipped servers)..."
curl -X GET "${BACKEND_URL}/api/bulk-ingestion-status" -s

echo ""
echo ""
echo "4. Waiting 10 more seconds..."
sleep 10

echo ""
echo "5. Final status check..."
curl -X GET "${BACKEND_URL}/api/bulk-ingestion-status" -s

echo ""
echo ""
echo "=== Test Complete ==="
echo ""
echo "Look for these fields in the JSON above:"
echo "- 'skipped_count': Should be ~22 (servers with unchanged content)"
echo "- 'completed_count': Should be ~2 (S922-G and S914 that need ingestion)"
echo "- 'force_reingest': Should be false"
echo ""
echo "Or check the UI - it should show the progress with skipped servers!"

# Made with Bob
