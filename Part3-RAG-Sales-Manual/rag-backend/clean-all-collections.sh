#!/bin/bash
# Clean All Collections Script
# Deletes all RAG collections from OpenSearch to prepare for fresh ingestion
# Collections are stored with MD5 hash names (e.g., rag_abc123def456...)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo "========================================"
echo "  Clean All Collections"
echo "========================================"
echo ""
echo -e "${YELLOW}⚠ WARNING: This will delete ALL RAG collections from OpenSearch${NC}"
echo -e "${GRAY}This includes all indices with prefix 'rag_' (hashed collection names)${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Operation cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Finding rag-backend pod...${NC}"

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    echo ""
    echo "Available pods:"
    oc get pods
    exit 1
fi

echo -e "${GREEN}✓ Found rag-backend pod: $POD${NC}"
echo ""

# List all collections first
echo -e "${YELLOW}Listing all RAG collections...${NC}"

LIST_SCRIPT="
import os
import hashlib
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))
OPENSEARCH_DB_PREFIX = os.environ.get('OPENSEARCH_DB_PREFIX', 'rag').lower()

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

# Get all indices that match our pattern (rag_*)
try:
    indices = client.indices.get_alias(index=f'{OPENSEARCH_DB_PREFIX}_*')
    for index_name in sorted(indices.keys()):
        try:
            doc_count = client.count(index=index_name)['count']
            print(f'{index_name}:{doc_count}')
        except Exception as e:
            print(f'{index_name}:ERROR', file=sys.stderr)
except Exception as e:
    print(f'No indices found or error: {e}', file=sys.stderr)
"

COLLECTIONS=$(echo "$LIST_SCRIPT" | oc exec -i $POD -- python 2>&1 | grep "^rag_")

if [ -z "$COLLECTIONS" ]; then
    echo -e "${GREEN}✓ No collections found${NC}"
    echo ""
    echo "Nothing to clean. You can proceed with fresh ingestion."
    exit 0
fi

echo -e "${CYAN}Found collections (hashed index names):${NC}"
echo "$COLLECTIONS" | while IFS=: read -r collection count; do
    echo -e "${GRAY}  - $collection ($count documents)${NC}"
done

COLLECTION_COUNT=$(echo "$COLLECTIONS" | wc -l)
echo ""
echo -e "${YELLOW}Total collections to delete: $COLLECTION_COUNT${NC}"
echo ""
read -p "Proceed with deletion? (yes/no): " confirm_delete

if [ "$confirm_delete" != "yes" ]; then
    echo -e "${YELLOW}Operation cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Deleting collections...${NC}"
echo ""

DELETED=0
FAILED=0

while IFS=: read -r collection count; do
    echo -e "${GRAY}Deleting $collection ($count docs)...${NC}"
    
    DELETE_SCRIPT="
import os
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

try:
    client.indices.delete(index='$collection')
    print('DELETED')
except Exception as e:
    print(f'ERROR:{e}')
"
    
    RESULT=$(echo "$DELETE_SCRIPT" | oc exec -i $POD -- python 2>&1 | grep -E "DELETED|ERROR")
    
    if echo "$RESULT" | grep -q "DELETED"; then
        echo -e "${GREEN}  ✓ Deleted $collection${NC}"
        DELETED=$((DELETED + 1))
    else
        echo -e "${RED}  ✗ Failed to delete $collection${NC}"
        echo -e "${RED}     $RESULT${NC}"
        FAILED=$((FAILED + 1))
    fi
done <<< "$COLLECTIONS"

echo ""
echo "========================================"
echo -e "${CYAN}  CLEANUP COMPLETE${NC}"
echo "========================================"
echo ""
echo -e "${GRAY}Summary:${NC}"
echo -e "${GREEN}  Deleted: $DELETED collections${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}  Failed: $FAILED collections${NC}"
fi
echo ""

# Verify cleanup
echo -e "${YELLOW}Verifying cleanup...${NC}"
VERIFY_SCRIPT="
import os
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))
OPENSEARCH_DB_PREFIX = os.environ.get('OPENSEARCH_DB_PREFIX', 'rag').lower()

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

try:
    indices = client.indices.get_alias(index=f'{OPENSEARCH_DB_PREFIX}_*')
    if indices:
        print(f'REMAINING:{len(indices)}')
        for idx in indices.keys():
            print(f'  {idx}')
    else:
        print('CLEAN')
except Exception:
    print('CLEAN')
"

VERIFY_RESULT=$(echo "$VERIFY_SCRIPT" | oc exec -i $POD -- python 2>&1)

if echo "$VERIFY_RESULT" | grep -q "CLEAN"; then
    echo -e "${GREEN}✓ All collections successfully deleted${NC}"
elif echo "$VERIFY_RESULT" | grep -q "REMAINING"; then
    echo -e "${YELLOW}⚠ Some collections still remain:${NC}"
    echo "$VERIFY_RESULT" | grep -v "REMAINING"
else
    echo -e "${GRAY}Verification result:${NC}"
    echo "$VERIFY_RESULT"
fi

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Start fresh bulk ingestion from the frontend UI"
echo "     - Navigate to the UI and trigger bulk ingestion"
echo "     - All servers will be re-scraped and ingested with enhanced chunking"
echo ""
echo "  2. Or test single server ingestion:"
echo "     ./test-e980-ingestion.sh"
echo ""
echo "  3. Monitor ingestion progress:"
echo "     oc logs -f $POD"
echo ""

# Made with Bob