#!/bin/bash
# Manual E980 Ingestion Test
# Uses the correct E980 content we scraped earlier

set -e

echo "=== E980 Manual Ingestion Test ==="
echo ""

BACKEND_URL="https://rag-backend-llm-on-techzone.apps.p1265.cecc.ihost.com"

# Check if we have the correct scraped content from earlier test
if [ ! -f "rag-backend/e980-scraped.json" ]; then
    echo "✗ E980 scraped content not found at rag-backend/e980-scraped.json"
    echo ""
    echo "Please run the scraper test first:"
    echo "  cd rag-backend"
    echo "  bash test-scraper-endpoints.sh"
    exit 1
fi

echo "Using scraped content from: rag-backend/e980-scraped.json"
echo ""

# Send to backend
echo "Sending to backend..."
echo "URL: $BACKEND_URL/ingest-scraped-content"
echo ""

RESPONSE=$(curl -s -X POST "$BACKEND_URL/ingest-scraped-content" \
    -H "Content-Type: application/json" \
    -d @rag-backend/e980-scraped.json \
    --max-time 120 \
    -w "\nHTTP_CODE:%{http_code}")

# Extract HTTP code
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Ingestion successful!"
    echo ""
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    
    # Save response
    echo "$BODY" > e980-ingestion-result.json
    echo ""
    echo "Saved to: e980-ingestion-result.json"
else
    echo "✗ Ingestion failed"
    echo "$BODY"
    exit 1
fi

# Made with Bob
