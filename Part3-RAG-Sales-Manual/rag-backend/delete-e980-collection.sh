#!/bin/bash
# Delete E980 Collection Before Reingest

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "====================================="
echo "  Delete E980 Collection"
echo "====================================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found pod: $POD${NC}"
echo ""

# E980 collection (hashed name)
COLLECTION="rag_d0f9e9bb718684771b4eb639bf167a2d"

echo -e "${YELLOW}Checking if collection exists...${NC}"

CHECK_COLLECTION="
import os
from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{'host': 'opensearch-service', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

collection = '$COLLECTION'

if client.indices.exists(index=collection):
    count = client.count(index=collection)['count']
    print(f'EXISTS:{count}')
else:
    print('NOT_EXISTS')
"

RESULT=$(echo "$CHECK_COLLECTION" | oc exec -i $POD -- python 2>&1 | grep -E "EXISTS|NOT_EXISTS")

if echo "$RESULT" | grep -q "EXISTS:"; then
    DOC_COUNT=$(echo "$RESULT" | sed 's/EXISTS://')
    echo -e "${YELLOW}⚠ Collection exists with $DOC_COUNT documents${NC}"
    echo ""
    echo -e "${CYAN}Collection: $COLLECTION${NC}"
    echo -e "${CYAN}MTM: 9080-M9S (E980)${NC}"
    echo ""
    read -p "Delete this collection? (yes/no): " response
    
    if [ "$response" != "yes" ]; then
        echo -e "${YELLOW}Deletion cancelled${NC}"
        exit 0
    fi
    
    echo ""
    echo -e "${YELLOW}Deleting collection...${NC}"
    
    DELETE_SCRIPT="
import os
from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{'host': 'opensearch-service', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

client.indices.delete(index='$COLLECTION')
print('DELETED')
"
    
    echo "$DELETE_SCRIPT" | oc exec -i $POD -- python 2>&1
    echo -e "${GREEN}✓ Collection deleted successfully${NC}"
else
    echo -e "${GREEN}✓ Collection does not exist${NC}"
fi

echo ""
echo "====================================="
echo -e "${GREEN}  Ready for Reingest${NC}"
echo "====================================="
echo ""
echo "Next steps:"
echo "  1. Rebuild backend: oc start-build rag-backend --from-dir=. --follow"
echo "  2. Re-ingest E980: ./test-e980-ingestion.sh"
echo ""

# Made with Bob
