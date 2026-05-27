#!/bin/bash
# Test Scraper Endpoints
# Checks what scraper is deployed and what endpoints it supports

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================="
echo "  Testing Scraper Endpoints"
echo "======================================="
echo ""

# Get scraper URL
if [ -f "scraper-url.txt" ]; then
    SCRAPER_URL=$(cat scraper-url.txt)
    echo -e "${GREEN}Using scraper URL from scraper-url.txt:${NC}"
    echo -e "${CYAN}  $SCRAPER_URL${NC}"
else
    echo -e "${YELLOW}Please provide the scraper service URL:${NC}"
    read -p "Scraper URL: " SCRAPER_URL
    
    if [ -z "$SCRAPER_URL" ]; then
        echo -e "${RED}Error: Scraper URL is required${NC}"
        exit 1
    fi
fi

echo ""
echo "======================================="
echo "  Testing Endpoints"
echo "======================================="
echo ""

# Test 1: Health endpoint
echo -e "${YELLOW}1. Testing /health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s -m 10 "$SCRAPER_URL/health" 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ /health endpoint works${NC}"
    echo "  Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ /health endpoint failed${NC}"
    echo "  Error: $HEALTH_RESPONSE"
fi

echo ""

# Test 2: Root endpoint
echo -e "${YELLOW}2. Testing / (root) endpoint...${NC}"
ROOT_RESPONSE=$(curl -s -m 10 "$SCRAPER_URL/" 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Root endpoint works${NC}"
    echo "  Response (first 300 chars): ${ROOT_RESPONSE:0:300}"
    echo ""
    echo "  Available endpoints:"
    echo "$ROOT_RESPONSE" | grep -o '"/[^"]*":"[^"]*"' | sed 's/"//g' | sed 's/^/    /'
else
    echo -e "${RED}✗ Root endpoint failed${NC}"
fi

echo ""

# Test 3: Scrape endpoint with GET and URL parameter
echo -e "${YELLOW}3. Testing /scrape endpoint with IBM docs URL...${NC}"
TEST_URL="https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s"
echo "  URL: $TEST_URL"
echo "  Method: GET with ?url= parameter"
echo "  This may take 30-60 seconds..."
echo ""

SCRAPE_START=$(date +%s)
# Use GET with URL parameter (URL-encoded)
ENCODED_URL=$(echo "$TEST_URL" | sed 's/:/%3A/g' | sed 's/\//%2F/g')
SCRAPE_RESPONSE=$(curl -s -m 120 "$SCRAPER_URL/scrape?url=$ENCODED_URL" 2>&1)
SCRAPE_END=$(date +%s)
SCRAPE_TIME=$((SCRAPE_END - SCRAPE_START))

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ /scrape endpoint works (took ${SCRAPE_TIME}s)${NC}"
    
    # Check content length
    CONTENT_LENGTH=${#SCRAPE_RESPONSE}
    echo "  Response size: $CONTENT_LENGTH bytes"
    
    # Check if content seems valid
    if [ $CONTENT_LENGTH -lt 500 ]; then
        echo -e "${RED}  ⚠ WARNING: Response seems too small${NC}"
        echo "  Full response (first 500 chars): ${SCRAPE_RESPONSE:0:500}"
    else
        echo -e "${GREEN}  Content appears valid${NC}"
        
        # Check for key indicators
        if echo "$SCRAPE_RESPONSE" | grep -q "Product life cycle"; then
            echo -e "${GREEN}  ✓ Contains 'Product life cycle'${NC}"
        else
            echo -e "${YELLOW}  ⚠ Does not contain 'Product life cycle'${NC}"
        fi
        
        if echo "$SCRAPE_RESPONSE" | grep -q "#[A-Z0-9]\{4\}"; then
            FEATURE_COUNT=$(echo "$SCRAPE_RESPONSE" | grep -o "#[A-Z0-9]\{4\}" | sort -u | wc -l)
            echo -e "${GREEN}  ✓ Contains $FEATURE_COUNT unique feature codes${NC}"
        else
            echo -e "${YELLOW}  ⚠ Does not contain feature codes${NC}"
        fi
        
        if echo "$SCRAPE_RESPONSE" | grep -q "activation"; then
            echo -e "${GREEN}  ✓ Contains 'activation' keyword${NC}"
        fi
        
        # Save response
        echo "$SCRAPE_RESPONSE" > test_scrape_response.txt
        echo "  Saved to: test_scrape_response.txt"
    fi
else
    echo -e "${RED}✗ /scrape endpoint failed${NC}"
    echo "  Error: $SCRAPE_RESPONSE"
fi

echo ""
echo "======================================="
echo "  Summary"
echo "======================================="
echo ""

# Determine which scraper is deployed
if echo "$ROOT_RESPONSE" | grep -qi "Selenium"; then
    echo -e "${CYAN}Deployed Scraper: Selenium-based (Windows Scraper Service)${NC}"
    echo "  Method: Selenium + Chrome"
    echo "  API: GET /scrape?url=..."
elif echo "$ROOT_RESPONSE" | grep -qi "simple"; then
    echo -e "${CYAN}Deployed Scraper: simple_scraper.py${NC}"
    echo "  File: Part3-RAG-Sales-Manual/scraper-test/simple_scraper.py"
elif echo "$ROOT_RESPONSE" | grep -qi "enhanced"; then
    echo -e "${CYAN}Deployed Scraper: enhanced_chromium_scraper.py${NC}"
    echo "  File: Part3-RAG-Sales-Manual/scraper-test/enhanced_chromium_scraper.py"
else
    echo -e "${YELLOW}Deployed Scraper: Unknown (check root response above)${NC}"
fi

echo ""
echo -e "${YELLOW}Recommendations:${NC}"

if [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -lt 500 ]; then
    echo "  - The scraper returned very little content"
    echo "  - Check if the URL is accessible"
    echo "  - Verify the scraper service is working correctly"
elif [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -gt 10000 ]; then
    echo "  - Scraper is working correctly!"
    echo "  - Content size: $CONTENT_LENGTH bytes"
    echo "  - Ready for E980 ingestion test"
    echo ""
    echo "  Next step:"
    echo "    ./test-e980-ingestion.sh"
else
    echo "  - Scraper returned some content but may be incomplete"
    echo "  - Review test_scrape_response.txt to verify quality"
fi

echo ""

# Made with Bob
