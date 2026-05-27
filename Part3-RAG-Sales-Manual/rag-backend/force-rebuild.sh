#!/bin/bash
# Force clean rebuild from correct directory

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "====================================="
echo "  Force Clean Rebuild"
echo "====================================="
echo ""

# Ensure we're in the rag-backend directory
cd C:/Users/029878866/EMEA-AI-SQUAD/RAG-with-Notebook/Part3-RAG-Sales-Manual/rag-backend

echo -e "${YELLOW}Current directory:${NC}"
pwd
echo ""

echo -e "${YELLOW}Verifying local code has dash filter...${NC}"
if grep -q "feature_name.startswith('-')" sales_manual_chunker.py; then
    echo -e "${GREEN}✓ Dash filter found in local file (line 207)${NC}"
else
    echo -e "${RED}✗ Dash filter NOT in local file!${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Starting build from current directory...${NC}"
echo -e "${GRAY}This will upload ALL files in: $(pwd)${NC}"
echo ""

# Start build with explicit path
oc start-build rag-backend --from-dir=. --follow

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Build complete${NC}"
echo ""

echo -e "${YELLOW}Forcing new deployment...${NC}"
oc rollout restart deployment/rag-backend

echo ""
echo -e "${YELLOW}Waiting for rollout...${NC}"
oc rollout status deployment/rag-backend

echo ""
echo -e "${GREEN}✓ Rollout complete${NC}"
echo ""

echo -e "${YELLOW}Waiting 10 seconds for pod to fully start...${NC}"
sleep 10

echo ""
echo -e "${YELLOW}Verifying code in new pod...${NC}"
./check-chunker-version.sh

echo ""
echo "====================================="

# Made with Bob
