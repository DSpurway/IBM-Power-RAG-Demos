#!/bin/bash
# Debug what's actually in the pod vs local

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "====================================="
echo "  Debug Build Issue"
echo "====================================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

echo -e "${CYAN}Local file (lines 200-215):${NC}"
sed -n '200,215p' sales_manual_chunker.py | cat -n

echo ""
echo -e "${CYAN}Pod file (lines 200-215):${NC}"
oc exec $POD -- sed -n '200,215p' /app/sales_manual_chunker.py | cat -n

echo ""
echo -e "${YELLOW}Checking BuildConfig source...${NC}"
oc get bc rag-backend -o yaml | grep -A 10 "source:"

echo ""
echo -e "${YELLOW}Checking if BuildConfig uses Git or Binary...${NC}"
oc get bc rag-backend -o jsonpath='{.spec.source.type}'
echo ""

echo ""
echo "====================================="

# Made with Bob
