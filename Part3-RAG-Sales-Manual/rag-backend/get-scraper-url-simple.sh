#!/bin/bash
# Get Scraper URL - Simple version without jq dependency
# Uses the known project ID to get the scraper URL

echo "======================================="
echo "  Getting Scraper Service URL"
echo "======================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ID="585c7939-e777-40a1-a8a9-484c80614776"
RESOURCE_GROUP="default"

echo -e "${YELLOW}Targeting resource group: $RESOURCE_GROUP${NC}"
ibmcloud target -g $RESOURCE_GROUP > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to target resource group${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Resource group targeted${NC}"
echo ""

echo -e "${YELLOW}Selecting Code Engine project...${NC}"
ibmcloud ce project select --id $PROJECT_ID > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to select project${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Project selected${NC}"
echo ""

echo -e "${YELLOW}Finding scraper applications...${NC}"
echo ""

# List applications and show them
ibmcloud ce application list

echo ""
echo -e "${YELLOW}Available scrapers:${NC}"
echo "  [1] ibm-docs-scraper (older)"
echo "  [2] ibm-docs-scraper-enhanced (newer, recommended)"
echo ""

read -p "Select scraper (1 or 2, default=2): " choice

if [ -z "$choice" ] || [ "$choice" = "2" ]; then
    APP_NAME="ibm-docs-scraper-enhanced"
else
    APP_NAME="ibm-docs-scraper"
fi

echo ""
echo -e "${CYAN}Selected: $APP_NAME${NC}"
echo ""

echo -e "${YELLOW}Getting $APP_NAME URL...${NC}"

# Get application details and extract URL without jq
APP_OUTPUT=$(ibmcloud ce application get --name $APP_NAME 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}Could not find $APP_NAME application${NC}"
    exit 1
fi

# Extract URL from output (look for https:// line)
SCRAPER_URL=$(echo "$APP_OUTPUT" | grep -o 'https://[^[:space:]]*' | head -1)

if [ -z "$SCRAPER_URL" ]; then
    echo -e "${RED}Could not extract URL from application details${NC}"
    echo ""
    echo "Application output:"
    echo "$APP_OUTPUT"
    exit 1
fi

echo "========================================"
echo -e "${CYAN}  SCRAPER SERVICE FOUND${NC}"
echo "========================================"
echo ""
echo "Application: $APP_NAME"
echo ""
echo -e "${YELLOW}Scraper URL:${NC}"
echo -e "${GREEN}  $SCRAPER_URL${NC}"
echo ""

# Test the scraper
echo -e "${YELLOW}Testing scraper health endpoint...${NC}"

HEALTH_RESPONSE=$(curl -s -m 10 "$SCRAPER_URL/health" 2>&1)

if [ $? -eq 0 ] && echo "$HEALTH_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✓ Scraper is healthy!${NC}"
    echo "  Response: $HEALTH_RESPONSE"
else
    echo -e "${YELLOW}⚠ Could not reach scraper health endpoint${NC}"
    echo "  The service may still be starting up"
fi

echo ""
echo "========================================"
echo ""
echo -e "${YELLOW}Use this URL for E980 ingestion:${NC}"
echo -e "${GREEN}  $SCRAPER_URL${NC}"
echo ""

# Save to file
echo "$SCRAPER_URL" > scraper-url.txt
echo "URL saved to: scraper-url.txt"
echo ""
echo -e "${YELLOW}Next step:${NC}"
echo "  ./test-e980-ingestion.sh"
echo ""

# Made with Bob
