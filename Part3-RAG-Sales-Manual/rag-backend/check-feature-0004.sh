#!/bin/bash
# Check Feature #0004 metadata and source

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

echo "====================================="
echo "  Feature #0004 Investigation"
echo "====================================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

COLLECTION="rag_d0f9e9bb718684771b4eb639bf167a2d"

echo -e "${YELLOW}Searching for all #0004 feature code chunks...${NC}"
echo ""

CHECK_0004="
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

# Search for feature code 0004
result = client.search(
    index=collection,
    body={
        'size': 10,
        'query': {
            'bool': {
                'must': [
                    {'match': {'metadata.section_type': 'feature_code'}},
                    {'term': {'metadata.feature_code.keyword': '0004'}}
                ]
            }
        }
    }
)

print(f'Found {result[\"hits\"][\"total\"][\"value\"]} chunks with feature code #0004')
print('=' * 80)
print()

for i, hit in enumerate(result['hits']['hits'], 1):
    metadata = hit['_source']['metadata']
    text = hit['_source']['text']
    
    print(f'Chunk {i}:')
    print('-' * 80)
    print(f'Feature Code: #{metadata.get(\"feature_code\")}')
    print(f'Feature Name: {metadata.get(\"feature_name\")}')
    print(f'Server Name: {metadata.get(\"server_name\")}')
    print(f'MTM: {metadata.get(\"mtm\")}')
    print(f'Source URL: {metadata.get(\"source\")}')
    print(f'Section Title: {metadata.get(\"section_title\")}')
    print(f'Withdrawn: {metadata.get(\"is_withdrawn\")}')
    if metadata.get('withdrawal_date'):
        print(f'Withdrawal Date: {metadata.get(\"withdrawal_date\")}')
    print(f'Chunk Strategy: {metadata.get(\"chunk_strategy\")}')
    print(f'Section Level: {metadata.get(\"section_level\", \"N/A\")}')
    print(f'Content Hash: {metadata.get(\"content_hash\", \"N/A\")[:16]}...')
    print(f'Ingestion Time: {metadata.get(\"ingestion_timestamp\")}')
    print()
    print('Full Text:')
    print(text)
    print()
    print('=' * 80)
    print()
"

echo "$CHECK_0004" | oc exec -i $POD -- python 2>&1

echo ""
echo -e "${YELLOW}Checking for duplicate pattern across all feature codes...${NC}"
echo ""

CHECK_DUPLICATES="
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

# Get all feature codes
result = client.search(
    index=collection,
    body={
        'size': 10000,
        '_source': ['metadata.feature_code', 'metadata.feature_name', 'text'],
        'query': {
            'match': {
                'metadata.section_type': 'feature_code'
            }
        }
    }
)

# Count duplicates by feature code
feature_counts = Counter()
feature_details = {}

for hit in result['hits']['hits']:
    metadata = hit['_source']['metadata']
    text = hit['_source']['text']
    code = metadata.get('feature_code')
    name = metadata.get('feature_name', '')
    
    feature_counts[code] += 1
    
    if code not in feature_details:
        feature_details[code] = []
    feature_details[code].append({
        'name': name,
        'text_length': len(text),
        'text_preview': text[:100]
    })

# Find duplicates
duplicates = {code: count for code, count in feature_counts.items() if count > 1}

print(f'Total unique feature codes: {len(feature_counts)}')
print(f'Feature codes with duplicates: {len(duplicates)}')
print()

if duplicates:
    print('Top 10 duplicated feature codes:')
    print('=' * 80)
    for code, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f'  #{code}: {count} occurrences')
        for i, detail in enumerate(feature_details[code], 1):
            print(f'    {i}. {detail[\"name\"]} ({detail[\"text_length\"]} chars)')
            print(f'       Preview: {detail[\"text_preview\"]}...')
        print()
"

echo "$CHECK_DUPLICATES" | oc exec -i $POD -- python 2>&1

echo ""
echo "====================================="
echo -e "${GREEN}  Investigation Complete${NC}"
echo "====================================="

# Made with Bob
