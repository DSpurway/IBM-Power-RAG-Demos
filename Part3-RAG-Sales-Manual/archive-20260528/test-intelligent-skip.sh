#!/bin/bash
# Test the intelligent skip logic

echo "=== Testing Intelligent Skip Logic ==="
echo ""
echo "This will trigger bulk ingestion and show skip behavior"
echo ""

BACKEND_URL="https://rag-backend-rag-demo.apps.p1265.cecc.ihost.com"

echo "1. Starting bulk ingestion (intelligent skip enabled by default)..."
curl -X POST "${BACKEND_URL}/api/start-bulk-ingestion" \
  -H "Content-Type: application/json" \
  -s | jq '.'

echo ""
echo "2. Waiting 5 seconds for processing to start..."
sleep 5

echo ""
echo "3. Checking status (should show skipped servers)..."
curl -X GET "${BACKEND_URL}/api/bulk-ingestion-status" \
  -s | jq '{
    in_progress,
    current_server,
    completed_count,
    skipped_count,
    failed_count,
    total,
    force_reingest,
    skipped: .skipped[:3]
  }'

echo ""
echo "4. Waiting 10 more seconds..."
sleep 10

echo ""
echo "5. Final status check..."
curl -X GET "${BACKEND_URL}/api/bulk-ingestion-status" \
  -s | jq '{
    in_progress,
    current_server,
    completed_count,
    skipped_count,
    failed_count,
    total,
    skipped_servers: (.skipped | length),
    completed_servers: (.completed | length)
  }'

echo ""
echo "=== Test Complete ==="
echo ""
echo "Expected behavior:"
echo "- Most servers should be SKIPPED (content unchanged)"
echo "- Only S922-G and S914 should be RE-INGESTED (missing data)"
echo "- Total time: ~5-10 minutes instead of 45-60 minutes"

# Made with Bob
