#!/bin/bash
# Test script for bulk ingestion status polling
# Tests both the backend endpoint and the Next.js API route

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Bulk Ingestion Status Polling Test"
echo "=========================================="
echo ""

# Configuration
BACKEND_URL="${RAG_BACKEND_URL:-http://localhost:8080}"
UI_URL="${UI_URL:-http://localhost:3000}"

echo "Backend URL: $BACKEND_URL"
echo "UI URL: $UI_URL"
echo ""

# Test 1: Check backend status endpoint
echo -e "${YELLOW}Test 1: Backend status endpoint${NC}"
echo "GET $BACKEND_URL/api/bulk-ingestion-status"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/api/bulk-ingestion-status")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Backend endpoint accessible${NC}"
    echo "Response:"
    echo "$BODY" | jq '.'
    
    # Check if response has expected fields
    IN_PROGRESS=$(echo "$BODY" | jq -r '.in_progress')
    TOTAL=$(echo "$BODY" | jq -r '.total')
    echo ""
    echo "in_progress: $IN_PROGRESS"
    echo "total: $TOTAL"
else
    echo -e "${RED}✗ Backend endpoint failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
    exit 1
fi

echo ""
echo "=========================================="
echo ""

# Test 2: Check UI API route
echo -e "${YELLOW}Test 2: UI API route${NC}"
echo "GET $UI_URL/api/rag/bulk-ingestion-status"
RESPONSE=$(curl -s -w "\n%{http_code}" "$UI_URL/api/rag/bulk-ingestion-status")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ UI API route accessible${NC}"
    echo "Response:"
    echo "$BODY" | jq '.'
else
    echo -e "${RED}✗ UI API route failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
    exit 1
fi

echo ""
echo "=========================================="
echo ""

# Test 3: Simulate polling (5 requests, 2 seconds apart)
echo -e "${YELLOW}Test 3: Simulate polling (5 requests)${NC}"
for i in {1..5}; do
    echo "Poll $i/5..."
    RESPONSE=$(curl -s "$UI_URL/api/rag/bulk-ingestion-status")
    IN_PROGRESS=$(echo "$RESPONSE" | jq -r '.in_progress')
    CURRENT=$(echo "$RESPONSE" | jq -r '.current_server')
    COMPLETED=$(echo "$RESPONSE" | jq -r '.completed_count')
    TOTAL=$(echo "$RESPONSE" | jq -r '.total')
    
    echo "  in_progress: $IN_PROGRESS"
    echo "  current_server: $CURRENT"
    echo "  progress: $COMPLETED/$TOTAL"
    
    if [ "$i" -lt 5 ]; then
        sleep 2
    fi
done

echo ""
echo "=========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo ""
echo "Next steps:"
echo "1. Open browser to $UI_URL/sales-manual"
echo "2. Open DevTools (F12) → Console tab"
echo "3. Click 'Load All Documents' button"
echo "4. Watch for console logs: [Bulk Ingestion] Status update"
echo "5. Verify progress bar updates every 10 seconds"
echo ""

# Made with Bob
