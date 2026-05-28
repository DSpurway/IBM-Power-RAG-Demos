#!/bin/bash
# Check Code Engine scraper health and warm it up if needed

SCRAPER_URL="https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud"

echo "================================================================================"
echo "  Code Engine Scraper Health Check"
echo "================================================================================"
echo ""
echo "Scraper URL: $SCRAPER_URL"
echo ""

echo "[1/3] Checking scraper health endpoint..."
START_TIME=$(date +%s)
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME:%{time_total}" "${SCRAPER_URL}/health" 2>&1)
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "$HEALTH_RESPONSE"
echo ""

HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
RESPONSE_TIME=$(echo "$HEALTH_RESPONSE" | grep "TIME:" | cut -d: -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Scraper is UP and responding"
    echo "  Response time: ${RESPONSE_TIME}s"
else
    echo "✗ Scraper returned HTTP $HTTP_CODE"
    echo "  This might indicate cold start or error"
fi
echo ""

echo "[2/3] Testing scraper with a simple request (warm-up)..."
echo "Scraping a small test page to ensure container is fully started..."
TEST_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME:%{time_total}" \
  "${SCRAPER_URL}/scrape?url=https://www.ibm.com/docs/en/announcements/power-e1080-enterprise-server" 2>&1)

TEST_HTTP_CODE=$(echo "$TEST_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
TEST_TIME=$(echo "$TEST_RESPONSE" | grep "TIME:" | cut -d: -f2)

if [ "$TEST_HTTP_CODE" = "200" ]; then
    echo "✓ Scraper successfully processed test request"
    echo "  Response time: ${TEST_TIME}s"
    
    # Check if we got sections
    SECTIONS=$(echo "$TEST_RESPONSE" | grep -o '"sections":[0-9]*' | cut -d: -f2)
    if [ -n "$SECTIONS" ] && [ "$SECTIONS" -gt 0 ]; then
        echo "  Sections extracted: $SECTIONS"
        echo "✓ Scraper is FULLY OPERATIONAL"
    else
        echo "  Warning: Got 0 sections - scraper may need more time"
    fi
else
    echo "✗ Test scrape failed with HTTP $TEST_HTTP_CODE"
    echo "  Response time: ${TEST_TIME}s"
    echo "  Scraper may still be starting up (cold start)"
fi
echo ""

echo "[3/3] Recommendations..."
echo ""
if [ "$HTTP_CODE" = "200" ] && [ "$TEST_HTTP_CODE" = "200" ]; then
    echo "✓ Scraper is ready for bulk ingestion"
    echo ""
    echo "You can now safely run bulk ingestion:"
    echo "  POD=\$(oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')"
    echo "  oc exec \$POD -- curl -s -X POST http://localhost:8080/api/start-bulk-ingestion \\"
    echo "    -H \"Content-Type: application/json\""
else
    echo "⚠ Scraper needs warm-up time"
    echo ""
    echo "Wait 30-60 seconds and run this script again, OR"
    echo "Run bulk ingestion anyway - first few servers may fail but will succeed on retry"
fi

echo ""
echo "================================================================================"
echo "  Health Check Complete"
echo "================================================================================"

# Made with Bob
