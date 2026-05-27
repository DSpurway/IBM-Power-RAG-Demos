#!/bin/bash

# Complete E980 reingest with fixed chunker
# This script deletes the old collection and reingests with the corrected code

echo "========================================="
echo "  Complete E980 Reingest (Fixed)"
echo "========================================="
echo ""

# Step 1: Delete existing E980 collection
echo "Step 1: Deleting existing E980 collection..."
COLLECTION_HASH="rag_d0f9e9bb718684771b4eb639bf167a2d"

POD_NAME=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
echo "Using pod: $POD_NAME"

oc exec $POD_NAME -- python3 -c "
from opensearchpy import OpenSearch
import os

client = OpenSearch(
    hosts=[{'host': os.getenv('OPENSEARCH_HOST', 'opensearch-cluster-master.rag-sales-manual.svc.cluster.local'), 'port': 9200}],
    http_auth=(os.getenv('OPENSEARCH_USER', 'admin'), os.getenv('OPENSEARCH_PASSWORD')),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False
)

collection = '$COLLECTION_HASH'
if client.indices.exists(index=collection):
    client.indices.delete(index=collection)
    print(f'✓ Deleted collection: {collection}')
else:
    print(f'Collection {collection} does not exist')
"

echo ""
echo "Step 2: Waiting for pod to be ready..."
sleep 5

# Step 3: Reingest E980
echo ""
echo "Step 3: Reingesting E980 with fixed chunker..."
echo ""

oc exec $POD_NAME -- python3 -c "
import sys
sys.path.insert(0, '/app')

from sales_manual_chunker import SalesManualChunker
from opensearch_manager import OpenSearchManager
import json
import os

# Load scraped data
with open('/app/data/e980_scraped_response.json', 'r') as f:
    data = json.load(f)

# Initialize
chunker = SalesManualChunker()
opensearch = OpenSearchManager()

# Process
chunks = chunker.chunk_sales_manual(data)
print(f'Generated {len(chunks)} chunks')

# Count by type
feature_codes = [c for c in chunks if c.get('metadata', {}).get('section_type') == 'feature_code']
lifecycle = [c for c in chunks if c.get('metadata', {}).get('section_type') == 'lifecycle_table']
sections = [c for c in chunks if c.get('metadata', {}).get('section_type') not in ['feature_code', 'lifecycle_table']]

print(f'  - Feature codes: {len(feature_codes)}')
print(f'  - Lifecycle table: {len(lifecycle)}')
print(f'  - Content sections: {len(sections)}')

# Ingest
collection_name = 'rag_mtm_9080_m9s'
opensearch.ingest_chunks(chunks, collection_name)
print(f'✓ Ingested to collection: {collection_name}')
"

echo ""
echo "========================================="
echo "  Reingest Complete!"
echo "========================================="
echo ""
echo "Expected results:"
echo "  - Feature codes: ~1,017 (NO duplicates)"
echo "  - Lifecycle table: 1"
echo "  - Content sections: ~2,237"
echo "  - Total: ~3,255 chunks"
echo ""
echo "Run ./inspect-e980-chunks.sh to verify"

# Made with Bob
