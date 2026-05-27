#!/bin/bash
# Hotfix: Copy file directly to pod to test

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "====================================="
echo "  Hotfix: Direct File Copy to Pod"
echo "====================================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

echo -e "${YELLOW}Copying sales_manual_chunker.py to pod...${NC}"
oc cp sales_manual_chunker.py $POD:/app/sales_manual_chunker.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ File copied${NC}"
else
    echo -e "${RED}✗ Copy failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Verifying file in pod...${NC}"
./check-chunker-version.sh

echo ""
echo -e "${YELLOW}Note: This is a temporary fix!${NC}"
echo -e "${GRAY}The file will be lost if the pod restarts.${NC}"
echo -e "${GRAY}We need to fix the Dockerfile/build process.${NC}"
echo ""

# Made with Bob
