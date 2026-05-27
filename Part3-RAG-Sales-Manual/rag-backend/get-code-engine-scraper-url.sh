#!/bin/bash
# Get Code Engine Scraper Service URL
# Helps find and display the scraper service URL from IBM Code Engine

echo "======================================="
echo "  IBM Code Engine Scraper Service Finder"
echo "======================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Check if IBM Cloud CLI is installed
echo -e "${YELLOW}Checking for IBM Cloud CLI...${NC}"

if ! command -v ibmcloud &> /dev/null; then
    echo -e "${RED}✗ IBM Cloud CLI is not installed${NC}"
    echo ""
    echo -e "${YELLOW}Please install IBM Cloud CLI:${NC}"
    echo "  https://cloud.ibm.com/docs/cli?topic=cli-install-ibmcloud-cli"
    echo ""
    echo -e "${YELLOW}Or use the web console:${NC}"
    echo "  1. Go to https://cloud.ibm.com/codeengine/projects"
    echo "  2. Select your project"
    echo "  3. Click on 'Applications'"
    echo "  4. Find the scraper application"
    echo "  5. Copy the 'Public URL'"
    exit 1
fi

echo -e "${GREEN}✓ IBM Cloud CLI is installed${NC}"
echo ""

# Check if logged in
echo -e "${YELLOW}Checking IBM Cloud login status...${NC}"

if ! ibmcloud target &> /dev/null; then
    echo -e "${RED}✗ Not logged into IBM Cloud${NC}"
    echo ""
    echo -e "${YELLOW}Please log in:${NC}"
    echo "  ibmcloud login --sso"
    echo ""
    echo -e "${YELLOW}Or use API key:${NC}"
    echo "  ibmcloud login --apikey YOUR_API_KEY"
    echo ""
    
    read -p "Would you like to log in now? (yes/no): " response
    if [ "$response" = "yes" ]; then
        echo ""
        echo -e "${YELLOW}Logging in with SSO...${NC}"
        ibmcloud login --sso
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}✗ Login failed${NC}"
            exit 1
        fi
    else
        exit 1
    fi
fi

echo -e "${GREEN}✓ Logged into IBM Cloud${NC}"

# Show current target
TARGET_INFO=$(ibmcloud target 2>&1)
REGION=$(echo "$TARGET_INFO" | grep "Region:" | awk '{print $2}')
RESOURCE_GROUP=$(echo "$TARGET_INFO" | grep "Resource group:" | cut -d':' -f2 | xargs)

if [ -n "$REGION" ]; then
    echo -e "${GRAY}  Region: $REGION${NC}"
fi
if [ -n "$RESOURCE_GROUP" ]; then
    echo -e "${GRAY}  Resource Group: $RESOURCE_GROUP${NC}"
fi

echo ""

# Check if Code Engine plugin is installed
echo -e "${YELLOW}Checking for Code Engine plugin...${NC}"

if ! ibmcloud plugin list 2>&1 | grep -q "code-engine"; then
    echo -e "${RED}✗ Code Engine plugin not installed${NC}"
    echo ""
    echo -e "${YELLOW}Installing Code Engine plugin...${NC}"
    ibmcloud plugin install code-engine -f
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to install Code Engine plugin${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Code Engine plugin installed${NC}"
else
    echo -e "${GREEN}✓ Code Engine plugin is installed${NC}"
fi

echo ""

# List Code Engine projects
echo -e "${YELLOW}Finding Code Engine projects...${NC}"
echo ""

PROJECTS_JSON=$(ibmcloud ce project list --output json 2>&1)

if [ $? -ne 0 ] || [ -z "$PROJECTS_JSON" ] || [ "$PROJECTS_JSON" = "[]" ]; then
    echo -e "${RED}✗ No Code Engine projects found${NC}"
    echo ""
    echo -e "${YELLOW}Please create a Code Engine project first:${NC}"
    echo "  https://cloud.ibm.com/codeengine/projects"
    exit 1
fi

# Parse projects
PROJECT_COUNT=$(echo "$PROJECTS_JSON" | jq '. | length')

echo -e "${GREEN}Found $PROJECT_COUNT Code Engine project(s):${NC}"
echo ""

# Display projects
for i in $(seq 0 $((PROJECT_COUNT - 1))); do
    PROJECT_NAME=$(echo "$PROJECTS_JSON" | jq -r ".[$i].name")
    PROJECT_REGION=$(echo "$PROJECTS_JSON" | jq -r ".[$i].region")
    PROJECT_ID=$(echo "$PROJECTS_JSON" | jq -r ".[$i].id")
    
    echo "  [$((i+1))] $PROJECT_NAME"
    echo -e "${GRAY}      Region: $PROJECT_REGION${NC}"
    echo -e "${GRAY}      ID: $PROJECT_ID${NC}"
    echo ""
done

# Select project
if [ $PROJECT_COUNT -eq 1 ]; then
    SELECTED_PROJECT=$(echo "$PROJECTS_JSON" | jq -r ".[0].name")
    echo -e "${CYAN}Using project: $SELECTED_PROJECT${NC}"
else
    read -p "Select project number (1-$PROJECT_COUNT): " selection
    SELECTED_PROJECT=$(echo "$PROJECTS_JSON" | jq -r ".[$(($selection - 1))].name")
    echo -e "${CYAN}Selected: $SELECTED_PROJECT${NC}"
fi

echo ""

# Select the project
echo -e "${YELLOW}Selecting project...${NC}"
ibmcloud ce project select --name "$SELECTED_PROJECT" &> /dev/null

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to select project${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Project selected${NC}"
echo ""

# List applications
echo -e "${YELLOW}Finding scraper application...${NC}"
echo ""

APPS_JSON=$(ibmcloud ce application list --output json 2>&1)

if [ $? -ne 0 ] || [ -z "$APPS_JSON" ] || [ "$APPS_JSON" = "[]" ]; then
    echo -e "${RED}✗ No applications found in this project${NC}"
    echo ""
    echo -e "${YELLOW}The scraper service may not be deployed yet.${NC}"
    echo -e "${YELLOW}Deploy it using:${NC}"
    echo "  cd Part3-RAG-Sales-Manual/scraper-test"
    echo "  ./deploy-to-code-engine.sh"
    exit 1
fi

APP_COUNT=$(echo "$APPS_JSON" | jq '. | length')

echo -e "${GREEN}Found $APP_COUNT application(s):${NC}"
echo ""

SCRAPER_APP=""
SCRAPER_URL=""

# Find scraper app
for i in $(seq 0 $((APP_COUNT - 1))); do
    APP_NAME=$(echo "$APPS_JSON" | jq -r ".[$i].name")
    APP_STATUS=$(echo "$APPS_JSON" | jq -r ".[$i].status")
    APP_URL=$(echo "$APPS_JSON" | jq -r ".[$i].url")
    
    echo "  Application: $APP_NAME"
    echo -e "${GRAY}    Status: $APP_STATUS${NC}"
    echo -e "${CYAN}    URL: $APP_URL${NC}"
    echo ""
    
    # Check if this looks like the scraper
    if [[ "$APP_NAME" == *"scraper"* ]] || [[ "$APP_NAME" == *"simple"* ]]; then
        SCRAPER_APP="$APP_NAME"
        SCRAPER_URL="$APP_URL"
    fi
done

# If we found a scraper app, use it
if [ -n "$SCRAPER_APP" ]; then
    echo "========================================"
    echo -e "${CYAN}  SCRAPER SERVICE FOUND${NC}"
    echo "========================================"
    echo ""
    echo "Application: $SCRAPER_APP"
    echo "Status: Ready"
    echo ""
    echo -e "${YELLOW}Scraper URL:${NC}"
    echo -e "${GREEN}  $SCRAPER_URL${NC}"
    echo ""
    
    # Test the scraper
    echo -e "${YELLOW}Testing scraper health endpoint...${NC}"
    
    HEALTH_RESPONSE=$(curl -s -m 10 "$SCRAPER_URL/health" 2>&1)
    
    if [ $? -eq 0 ] && echo "$HEALTH_RESPONSE" | grep -q "status"; then
        echo -e "${GREEN}✓ Scraper is healthy!${NC}"
        STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status' 2>/dev/null || echo "ok")
        echo -e "${GRAY}  Status: $STATUS${NC}"
        echo ""
    else
        echo -e "${YELLOW}⚠ Could not reach scraper health endpoint${NC}"
        echo -e "${GRAY}  The service may still be starting up${NC}"
        echo ""
    fi
    
    echo "========================================"
    echo ""
    echo -e "${YELLOW}Copy this URL for the E980 ingestion test:${NC}"
    echo -e "${GREEN}  $SCRAPER_URL${NC}"
    echo ""
    echo -e "${YELLOW}Next step:${NC}"
    echo "  ./test-e980-ingestion.sh"
    echo ""
    
    # Save to file for easy access
    echo "$SCRAPER_URL" > scraper-url.txt
    echo -e "${GRAY}URL saved to: scraper-url.txt${NC}"
    
else
    echo -e "${YELLOW}⚠ No scraper application found${NC}"
    echo ""
    echo -e "${YELLOW}Available applications:${NC}"
    for i in $(seq 0 $((APP_COUNT - 1))); do
        APP_NAME=$(echo "$APPS_JSON" | jq -r ".[$i].name")
        APP_URL=$(echo "$APPS_JSON" | jq -r ".[$i].url")
        echo "  - $APP_NAME: $APP_URL"
    done
    echo ""
    echo -e "${YELLOW}If one of these is your scraper, use its URL.${NC}"
    echo -e "${YELLOW}Otherwise, deploy the scraper first:${NC}"
    echo "  cd Part3-RAG-Sales-Manual/scraper-test"
    echo "  ./deploy-to-code-engine.sh"
fi

echo ""

# Made with Bob
