#!/bin/bash
# Check if updated chunker code is running

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "====================================="
echo "  Check Chunker Version in Pod"
echo "====================================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found pod: $POD${NC}"
echo ""

echo -e "${YELLOW}Checking sales_manual_chunker.py in pod...${NC}"
echo ""

# Check if the dash filter code exists in the pod
CHECK_CODE="
import os
os.chdir('/app')

try:
    with open('sales_manual_chunker.py', 'r') as f:
        content = f.read()
        
    # Check for the dash filter
    if \"feature_name.startswith('-')\" in content:
        print('DASH_FILTER_FOUND')
        # Find and print the relevant lines
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'startswith' in line and 'dash' in line.lower():
                print(f'Line {i+1}: {line}')
                # Print surrounding context
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    print(f'  {j+1}: {lines[j]}')
                break
    else:
        print('DASH_FILTER_NOT_FOUND')
        print('Code does not contain dash filter!')
except Exception as e:
    print(f'ERROR: {e}')
"

echo "$CHECK_CODE" | oc exec -i $POD -- python 2>&1

echo ""
echo -e "${YELLOW}Checking recent logs for chunker debug messages...${NC}"
echo ""

oc logs $POD --tail=100 | grep -i "skipping feature code\|dash\|list item" || echo -e "${GRAY}No chunker debug messages found in recent logs${NC}"

echo ""
echo "====================================="

# Made with Bob
