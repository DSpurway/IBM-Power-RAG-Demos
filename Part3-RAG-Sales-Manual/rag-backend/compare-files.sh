#!/bin/bash
# Compare local vs pod files

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "====================================="
echo "  Compare Local vs Pod Files"
echo "====================================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

echo -e "${CYAN}Local file (lines 200-215):${NC}"
sed -n '200,215p' sales_manual_chunker.py | nl

echo ""
echo -e "${CYAN}Pod file (lines 200-215):${NC}"
oc exec $POD -- sh -c "sed -n '200,215p' /app/sales_manual_chunker.py" | nl

echo ""
echo -e "${YELLOW}Searching for dash filter in pod file:${NC}"
oc exec $POD -- sh -c "grep -n 'startswith' /app/sales_manual_chunker.py"

echo ""
echo "====================================="

# Made with Bob
