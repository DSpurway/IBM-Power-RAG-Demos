#!/bin/bash

# Identify what each collection contains

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

echo "Identifying Collections"
echo "======================="
echo ""

oc exec $POD -- python -c "
from opensearchpy import OpenSearch

c = OpenSearch([{'host':'opensearch-service','port':9200}],use_ssl=False)

collections = [i for i in c.indices.get_alias().keys() if 'rag' in i]

print(f'Total collections: {len(collections)}')
print('')

# Check E980 collection
e980_hash = 'rag_d0f9e9bb718684771b4eb639bf167a2d'
if e980_hash in collections:
    count = c.count(index=e980_hash)['count']
    # Get a sample doc to see MTM
    sample = c.search(index=e980_hash, body={'size': 1})
    if sample['hits']['hits']:
        mtm = sample['hits']['hits'][0]['_source'].get('metadata', {}).get('mtm', 'unknown')
        server = sample['hits']['hits'][0]['_source'].get('metadata', {}).get('server_name', 'unknown')
        print(f'E980 Collection: {e980_hash}')
        print(f'  Server: {server}')
        print(f'  MTM: {mtm}')
        print(f'  Documents: {count}')
        print('')

# Sample a few other collections
print('Other collections (sample):')
for coll in collections[:5]:
    if coll != e980_hash:
        try:
            count = c.count(index=coll)['count']
            sample = c.search(index=coll, body={'size': 1})
            if sample['hits']['hits']:
                mtm = sample['hits']['hits'][0]['_source'].get('metadata', {}).get('mtm', 'unknown')
                server = sample['hits']['hits'][0]['_source'].get('metadata', {}).get('server_name', 'unknown')
                print(f'{coll}: {server} ({mtm}) - {count} docs')
        except:
            print(f'{coll}: Error reading')
"

# Made with Bob
