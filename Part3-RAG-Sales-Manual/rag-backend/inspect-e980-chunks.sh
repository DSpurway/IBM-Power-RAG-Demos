#!/bin/bash
# Inspect E980 Collection Contents - Lifecycle Table and Feature Codes

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

echo "====================================="
echo "  E980 Collection Inspection"
echo "====================================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

# E980 collection (from previous search)
COLLECTION="rag_d0f9e9bb718684771b4eb639bf167a2d"

echo -e "${CYAN}Collection: $COLLECTION${NC}"
echo -e "${GRAY}MTM: 9080-M9S (E980)${NC}"
echo -e "${GRAY}Documents: 4,272${NC}"
echo ""

echo -e "${YELLOW}Step 1: Chunk Distribution${NC}"
echo "==========================="
echo ""

CHUNK_DIST="
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

result = client.search(
    index=collection,
    body={
        'size': 10000,
        '_source': ['metadata.section_type'],
        'query': {'match_all': {}}
    }
)

section_types = Counter()
for hit in result['hits']['hits']:
    section_type = hit['_source'].get('metadata', {}).get('section_type', 'unknown')
    section_types[section_type] += 1

print('Chunk Distribution:')
for section_type, count in sorted(section_types.items(), key=lambda x: x[1], reverse=True):
    print(f'  {section_type}: {count}')
"

echo "$CHUNK_DIST" | oc exec -i $POD -- python 2>&1

echo ""
echo -e "${YELLOW}Step 2: Product Life Cycle Dates Table${NC}"
echo "========================================"
echo ""

LIFECYCLE="
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
    
    print('✓ Lifecycle Table Found')
    print('=' * 80)
    print(text)
    print('=' * 80)
    print()
    print('Metadata:')
    print(f'  Section Type: {metadata.get(\"section_type\")}')
    print(f'  Section Title: {metadata.get(\"section_title\")}')
    print(f'  Priority: {metadata.get(\"priority\")}')
    print(f'  Query Type: {metadata.get(\"query_type\")}')
    print(f'  Chunk Strategy: {metadata.get(\"chunk_strategy\")}')
    print(f'  Content Hash: {metadata.get(\"content_hash\", \"N/A\")[:16]}...')
    print(f'  Ingestion Time: {metadata.get(\"ingestion_timestamp\")}')
else:
    print('✗ Lifecycle Table NOT FOUND')
"

echo "$LIFECYCLE" | oc exec -i $POD -- python 2>&1

echo ""
echo -e "${YELLOW}Step 3: Feature Code Samples${NC}"
echo "============================="
echo ""

FEATURES="
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

# Get total count
total_result = client.count(
    index=collection,
    body={
        'query': {
            'match': {
                'metadata.section_type': 'feature_code'
            }
        }
    }
)

print(f'Total Feature Codes: {total_result[\"count\"]}')
print()

# Get first 10 feature codes sorted by code
result = client.search(
    index=collection,
    body={
        'size': 10,
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

print('Sample Feature Codes (first 10):')
print('=' * 80)

for i, hit in enumerate(result['hits']['hits'], 1):
    metadata = hit['_source']['metadata']
    text = hit['_source']['text']
    
    print(f'{i}. #{metadata.get(\"feature_code\", \"N/A\")} - {metadata.get(\"feature_name\", \"N/A\")}')
    print(f'   Withdrawn: {metadata.get(\"is_withdrawn\", False)}')
    if metadata.get('withdrawal_date'):
        print(f'   Withdrawal Date: {metadata.get(\"withdrawal_date\")}')
    if metadata.get('csu') is not None:
        print(f'   CSU: {metadata.get(\"csu\")}')
    if metadata.get('minimum_required'):
        print(f'   Min Required: {metadata.get(\"minimum_required\")}')
    if metadata.get('maximum_allowed'):
        print(f'   Max Allowed: {metadata.get(\"maximum_allowed\")}')
    print(f'   Text Length: {len(text)} chars')
    
    # Show first 200 chars of text
    preview = text[:200].replace('\\n', ' ')
    print(f'   Preview: {preview}...')
    print()
"

echo "$FEATURES" | oc exec -i $POD -- python 2>&1

echo ""
echo -e "${YELLOW}Step 4: Check for Withdrawn Features${NC}"
echo "====================================="
echo ""

WITHDRAWN="
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

# Count withdrawn features
result = client.search(
    index=collection,
    body={
        'size': 5,
        'query': {
            'bool': {
                'must': [
                    {'match': {'metadata.section_type': 'feature_code'}},
                    {'term': {'metadata.is_withdrawn': True}}
                ]
            }
        },
        'sort': [
            {'metadata.feature_code.keyword': {'order': 'asc'}}
        ]
    }
)

total_withdrawn = client.count(
    index=collection,
    body={
        'query': {
            'bool': {
                'must': [
                    {'match': {'metadata.section_type': 'feature_code'}},
                    {'term': {'metadata.is_withdrawn': True}}
                ]
            }
        }
    }
)['count']

print(f'Total Withdrawn Features: {total_withdrawn}')
print()

if result['hits']['hits']:
    print('Sample Withdrawn Features:')
    print('=' * 80)
    for hit in result['hits']['hits']:
        metadata = hit['_source']['metadata']
        print(f'  #{metadata.get(\"feature_code\")} - {metadata.get(\"feature_name\")}')
        print(f'    Withdrawal Date: {metadata.get(\"withdrawal_date\", \"N/A\")}')
        print()
"

echo "$WITHDRAWN" | oc exec -i $POD -- python 2>&1

echo ""
echo "====================================="
echo -e "${GREEN}  Inspection Complete${NC}"
echo "====================================="
echo ""

# Made with Bob
