#!/bin/bash
# Find E980 Collection by MTM in metadata

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

echo "====================================="
echo "  Finding E980 Collection"
echo "====================================="
echo ""
echo -e "${GRAY}Looking for MTM: 9080-M9S${NC}"
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found pod: $POD${NC}"
echo ""

FIND_COLLECTION="
import os
from opensearchpy import OpenSearch
import hashlib

client = OpenSearch(
    hosts=[{'host': 'opensearch-service', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

# Get all collections
all_indices = [idx for idx in client.indices.get_alias().keys() if idx.startswith('rag_')]

print(f'Total collections: {len(all_indices)}')
print()

# Search each collection for E980 MTM
target_mtm = '9080-M9S'
found_collections = []

for collection in all_indices:
    try:
        result = client.search(
            index=collection,
            body={
                'size': 1,
                'query': {
                    'match': {
                        'metadata.mtm': target_mtm
                    }
                }
            }
        )
        
        if result['hits']['total']['value'] > 0:
            doc_count = client.count(index=collection)['count']
            hit = result['hits']['hits'][0]
            metadata = hit['_source'].get('metadata', {})
            
            found_collections.append({
                'collection': collection,
                'doc_count': doc_count,
                'server_name': metadata.get('server_name', 'N/A'),
                'mtm': metadata.get('mtm', 'N/A'),
                'ingestion_timestamp': metadata.get('ingestion_timestamp', 'N/A')
            })
    except Exception as e:
        pass

if found_collections:
    print(f'Found {len(found_collections)} collection(s) with MTM {target_mtm}:')
    print('=' * 80)
    for info in found_collections:
        print(f'Collection: {info[\"collection\"]}')
        print(f'  Server: {info[\"server_name\"]}')
        print(f'  MTM: {info[\"mtm\"]}')
        print(f'  Documents: {info[\"doc_count\"]}')
        print(f'  Ingested: {info[\"ingestion_timestamp\"]}')
        print('-' * 80)
    
    # Return the most recent collection
    latest = max(found_collections, key=lambda x: x['ingestion_timestamp'])
    print()
    print(f'LATEST_COLLECTION:{latest[\"collection\"]}')
else:
    print(f'No collections found with MTM {target_mtm}')
    print()
    print('Checking collection naming logic...')
    
    # Check if collections use hash-based naming
    sample_collection = all_indices[0] if all_indices else None
    if sample_collection:
        result = client.search(
            index=sample_collection,
            body={'size': 1, 'query': {'match_all': {}}}
        )
        if result['hits']['hits']:
            metadata = result['hits']['hits'][0]['_source'].get('metadata', {})
            print(f'Sample collection: {sample_collection}')
            print(f'  MTM in metadata: {metadata.get(\"mtm\", \"N/A\")}')
            print(f'  Server: {metadata.get(\"server_name\", \"N/A\")}')
"

echo "$FIND_COLLECTION" | oc exec -i $POD -- python 2>&1

# Made with Bob
