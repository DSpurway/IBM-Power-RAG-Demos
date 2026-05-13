#!/bin/bash
# Test Enhanced Scraper with Git Bash
# Run this in Git Bash terminal

SCRAPER_URL="https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud"
TEST_URL="https://www.ibm.com/docs/en/announcements/family-908005-power-e1180-enterprise-server-9080-heu"

echo "Testing Enhanced Scraper..."
echo "Scraper URL: $SCRAPER_URL"
echo "Test Document: IBM Power E1180"
echo ""

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s "$SCRAPER_URL/health" | python -m json.tool
echo ""

# Test scraping (this takes 20-30 seconds)
echo "2. Testing scrape endpoint (this may take 30-60 seconds)..."
RESPONSE=$(curl -s "$SCRAPER_URL/scrape?url=$TEST_URL")

# Check if successful
if echo "$RESPONSE" | grep -q '"success": true'; then
    echo "✓ Scrape successful!"
    echo ""
    
    # Extract key metrics
    echo "Results:"
    echo "$RESPONSE" | python -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Status: {data.get('success', False)}\")
print(f\"  Tables Found: {data.get('metadata', {}).get('tables_count', 0)}\")
print(f\"  Sections: {data.get('sections_count', 0)}\")
print(f\"  Withdrawal Dates: {len(data.get('metadata', {}).get('withdrawal_dates', []))}\")
print(f\"  Feature Codes: {len(data.get('metadata', {}).get('feature_codes', []))}\")
print(f\"  MTM Detected: {data.get('mtm', 'None')}\")
"
    echo ""
    echo "✓ Enhanced scraper is working correctly!"
else
    echo "✗ Scrape failed"
    echo "$RESPONSE" | python -m json.tool
fi

# Made with Bob
