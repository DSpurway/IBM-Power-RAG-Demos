#!/bin/bash
# Check E980 Vector Store Contents
# Examines lifecycle table and feature code chunks after reingest

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

echo "====================================="
echo "  E980 Vector Store Inspection"
echo "====================================="
echo ""

# Get rag-backend pod
POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found pod: $POD${NC}"
echo ""

# Expected collection for E980 (MTM: 9080-M9S)
COLLECTION="rag_mtm_9080_m9s"

echo -e "${YELLOW}Step 1: Check Collection Exists${NC}"
echo "================================"
echo ""

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
    echo -e "${GREEN}✓ Collection exists: $COLLECTION${NC}"
    echo -e "${CYAN}  Total documents: $DOC_COUNT${NC}"
else
    echo -e "${RED}✗ Collection not found: $COLLECTION${NC}"
    echo ""
    echo "Available collections:"
    oc exec $POD -- python -c "from opensearchpy import OpenSearch; c=OpenSearch([{'host':'opensearch-service','port':9200}],use_ssl=False); print('\n'.join([idx for idx in c.indices.get_alias().keys() if idx.startswith('rag_')]))"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 2: Analyze Chunk Distribution${NC}"
echo "===================================="
echo ""

CHUNK_DISTRIBUTION="
import os
from opensearchpy import OpenSearch
from collections import Counter

client = OpenSearch(
    hosts=[{'host': 'opensearch-service', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

collection = '$COLLECTION'

# Get all documents with section_type
result = client.search(
    index=collection,
    body={
        'size': 10000,
        '_source': ['metadata.section_type', 'metadata.section_title'],
        'query': {'match_all': {}}
    }
)

section_types = Counter()
for hit in result['hits']['hits']:
    section_type = hit['_source'].get('metadata', {}).get('section_type', 'unknown')
    section_types[section_type] += 1

print('CHUNK_DISTRIBUTION:')
for section_type, count in section_types.most_common():
    print(f'  {section_type}: {count}')
"

echo "$CHUNK_DISTRIBUTION" | oc exec -i $POD -- python 2>&1 | grep -A 20 "CHUNK_DISTRIBUTION:"

echo ""
echo -e "${YELLOW}Step 3: Inspect Lifecycle Table Chunk${NC}"
echo "======================================"
echo ""

LIFECYCLE_QUERY="
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

# Search for lifecycle table
result = client.search(
    index=collection,
    body={
        'size': 1,
        'query': {
            'match': {
                'metadata.section_type': 'lifecycle_table'
            }
        }
    }
)

if result['hits']['hits']:
    hit = result['hits']['hits'][0]
    text = hit['_source']['text']
    metadata = hit['_source']['metadata']
    
    print('LIFECYCLE_TABLE_FOUND')
    print('=' * 60)
    print(text)
    print('=' * 60)
    print()
    print('Metadata:')
    print(f'  MTM: {metadata.get(\"mtm\", \"N/A\")}')
    print(f'  Server: {metadata.get(\"server_name\", \"N/A\")}')
    print(f'  Priority: {metadata.get(\"priority\", \"N/A\")}')
    print(f'  Query Type: {metadata.get(\"query_type\", \"N/A\")}')
    print(f'  Chunk Strategy: {metadata.get(\"chunk_strategy\", \"N/A\")}')
    print(f'  Content Hash: {metadata.get(\"content_hash\", \"N/A\")[:16]}...')
    print(f'  Ingestion Time: {metadata.get(\"ingestion_timestamp\", \"N/A\")}')
else:
    print('LIFECYCLE_TABLE_NOT_FOUND')
"

echo "$LIFECYCLE_QUERY" | oc exec -i $POD -- python 2>&1

echo ""
echo -e "${YELLOW}Step 4: Sample Feature Code Chunks${NC}"
echo "==================================="
echo ""

FEATURE_QUERY="
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

# Get first 5 feature codes
result = client.search(
    index=collection,
    body={
        'size': 5,
        'query': {
            'match': {
                'metadata.section_type': 'feature_code'
            }
        },
        'sort': [
            {'metadata.feature_code.keyword': {'order': 'asc'}}
        ]
    }
)

print(f'Total Feature Codes: {result[\"hits\"][\"total\"][\"value\"]}')
print()
print('Sample Feature Codes:')
print('=' * 80)

for i, hit in enumerate(result['hits']['hits'], 1):
    metadata = hit['_source']['metadata']
    text = hit['_source']['text']
    
    print(f'{i}. Feature Code: #{metadata.get(\"feature_code\", \"N/A\")}')
    print(f'   Name: {metadata.get(\"feature_name\", \"N/A\")}')
    print(f'   Withdrawn: {metadata.get(\"is_withdrawn\", \"N/A\")}')
    if metadata.get('withdrawal_date'):
        print(f'   Withdrawal Date: {metadata.get(\"withdrawal_date\")}')
    print(f'   CSU: {metadata.get(\"csu\", \"N/A\")}')
    print(f'   Text Length: {len(text)} chars')
    print(f'   Preview: {text[:150]}...')
    print('-' * 80)
"

echo "$FEATURE_QUERY" | oc exec -i $POD -- python 2>&1

echo ""
echo -e "${YELLOW}Step 5: Check Collection Mapping${NC}"
echo "================================="
echo ""

MAPPING_QUERY="
import os
from opensearchpy import OpenSearch
import json

client = OpenSearch(
    hosts=[{'host': 'opensearch-service', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

collection = '$COLLECTION'

# Get mapping
mapping = client.indices.get_mapping(index=collection)

print('Collection Mapping:')
print('=' * 60)
print(json.dumps(mapping[collection]['mappings'], indent=2))
"

echo "$MAPPING_QUERY" | oc exec -i $POD -- python 2>&1 | head -50

echo ""
echo "====================================="
echo -e "${GREEN}  Inspection Complete${NC}"
echo "====================================="
echo ""
echo -e "${GRAY}Collection: $COLLECTION${NC}"
echo -e "${GRAY}Pod: $POD${NC}"
echo ""

# Made with Bob
