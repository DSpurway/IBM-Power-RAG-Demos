#!/bin/bash
# Identify which MTM the mystery index belongs to

echo "================================================================================"
echo "  Identifying Mystery Index with S924 Content"
echo "================================================================================"
echo ""

POD=$(oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

# The index with most S924 content (193 docs)
MYSTERY_INDEX="rag_b3798f254d623a343095d663f5f773b2"

echo "Mystery index: $MYSTERY_INDEX"
echo "This index has 193 documents matching 'S924' or '9009' or '42A'"
echo "Total documents in index: 3645"
echo ""

echo "[1/2] Getting a sample document from this index to see metadata..."
oc exec $POD -- curl -s -X GET "http://opensearch-service:9200/${MYSTERY_INDEX}/_search?size=1" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {"text": "9009-42A"}
    }
  }' | python -m json.tool | head -80
echo ""
echo ""

echo "[2/2] Checking which MTM this index hash corresponds to..."
echo "From the collections API, we know:"
echo "  rag_b3798f254d623a343095d663f5f773b2 = MTM 9009-41G (S914-G) with 3645 docs"
echo ""
echo "Wait... that's S914-G, not S924!"
echo ""
echo "This means S924 (9009-42A) content is being found in the S914-G collection!"
echo "This suggests a data contamination or ingestion error."
echo ""

# Made with Bob
