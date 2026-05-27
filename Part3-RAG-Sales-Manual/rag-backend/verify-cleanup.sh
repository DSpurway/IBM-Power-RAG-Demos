#!/bin/bash
# Verify Cleanup Script
# Quick check to see what collections exist in OpenSearch

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo "========================================"
echo "  Verify OpenSearch Cleanup"
echo "========================================"
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found rag-backend pod: $POD${NC}"
echo ""

echo -e "${YELLOW}Checking OpenSearch indices...${NC}"

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

print('=== All Indices ===')
try:
    all_indices = client.indices.get(index='*')
    for idx in sorted(all_indices.keys()):
        try:
            count = client.count(index=idx)['count']
            print(f'{idx}: {count} documents')
        except:
            print(f'{idx}: ERROR getting count')
except Exception as e:
    print(f'ERROR: {e}')

print('')
print(f'=== RAG Indices (prefix: {OPENSEARCH_DB_PREFIX}_) ===')
try:
    rag_indices = client.indices.get(index=f'{OPENSEARCH_DB_PREFIX}_*')
    if rag_indices:
        total_docs = 0
        for idx in sorted(rag_indices.keys()):
            try:
                count = client.count(index=idx)['count']
                total_docs += count
                print(f'{idx}: {count} documents')
            except:
                print(f'{idx}: ERROR getting count')
        print(f'')
        print(f'Total RAG documents: {total_docs}')
    else:
        print('No RAG indices found')
except Exception as e:
    print(f'No RAG indices found (this is expected after cleanup)')
"

echo "$VERIFY_SCRIPT" | oc exec -i $POD -- python

echo ""
echo "========================================"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "If you see RAG indices above:"
echo "  1. Run ./clean-all-collections.sh again"
echo "  2. Or manually delete specific indices"
echo ""
echo "If no RAG indices found:"
echo "  1. Refresh the frontend (Ctrl+F5 or Cmd+Shift+R)"
echo "  2. Click 'Refresh Status' button"
echo "  3. Start fresh ingestion"
echo ""

# Made with Bob