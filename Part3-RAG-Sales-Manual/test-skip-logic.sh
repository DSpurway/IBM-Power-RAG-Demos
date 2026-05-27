#!/bin/bash

# Test Intelligent Skip Logic
# This script tests the skip logic by running bulk ingestion twice
# First run should ingest all servers, second run should skip unchanged ones

set -e

echo "=========================================="
echo "Testing Intelligent Skip Logic"
echo "=========================================="
echo ""

# Get backend route
BACKEND_ROUTE=$(oc get route rag-backend -o jsonpath='{.spec.host}')
BACKEND_URL="https://$BACKEND_ROUTE"

echo "Backend URL: $BACKEND_URL"
echo ""

# Test 1: Check skip logic endpoint
echo "Test 1: Checking skip logic endpoint..."
echo ""

curl -s -k "$BACKEND_URL/api/start-bulk-ingestion" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.'

echo ""
echo "✓ Bulk ingestion started"
echo ""

# Wait for completion
echo "Waiting for bulk ingestion to complete..."
echo "This will take 45-60 minutes for first run..."
echo ""

# Monitor progress
while true; do
    STATUS=$(curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq -r '.status')
    COMPLETED=$(curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq -r '.completed')
    TOTAL=$(curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq -r '.total')
    SKIPPED=$(curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq -r '.skipped | length')
    
    echo "Status: $STATUS | Progress: $COMPLETED/$TOTAL | Skipped: $SKIPPED"
    
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "idle" ]; then
        break
    fi
    
    sleep 30
done

echo ""
echo "✓ First bulk ingestion complete"
echo ""

# Get final status
echo "Final status:"
curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq '.'

echo ""
echo "=========================================="
echo "Test 2: Second Run (Should Skip Most)"
echo "=========================================="
echo ""

# Wait a bit before second run
sleep 5

# Start second bulk ingestion
echo "Starting second bulk ingestion..."
curl -s -k "$BACKEND_URL/api/start-bulk-ingestion" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.'

echo ""
echo "Monitoring second run..."
echo ""

# Monitor second run
while true; do
    STATUS=$(curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq -r '.status')
    COMPLETED=$(curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq -r '.completed')
    TOTAL=$(curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq -r '.total')
    SKIPPED=$(curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq -r '.skipped | length')
    
    echo "Status: $STATUS | Progress: $COMPLETED/$TOTAL | Skipped: $SKIPPED"
    
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "idle" ]; then
        break
    fi
    
    sleep 10
done

echo ""
echo "✓ Second bulk ingestion complete"
echo ""

# Get final status with skip details
echo "Final status with skip details:"
curl -s -k "$BACKEND_URL/api/bulk-ingestion-status" | jq '.'

echo ""
echo "=========================================="
echo "Skip Logic Test Complete!"
echo "=========================================="
echo ""
echo "Expected Results:"
echo "- First run: 0 skipped, all 26 servers ingested"
echo "- Second run: ~24 skipped (unchanged), ~2 re-ingested"
echo ""
echo "Skipped servers should have reason: 'unchanged'"
echo "Re-ingested servers: S922-G, S914 (known to change)"
echo ""

# Made with Bob
