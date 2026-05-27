#!/bin/bash
# Check ALL OpenSearch indices to find S924 data

echo "================================================================================"
echo "  Checking ALL OpenSearch Indices"
echo "================================================================================"
echo ""

POD=$(oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
echo "Using pod: $POD"
echo ""

echo "[1/3] Getting ALL indices from OpenSearch..."
oc exec $POD -- curl -s http://opensearch-service:9200/_cat/indices?v
echo ""
echo ""

echo "[2/3] Searching for indices with 'S924' or '9009' or '42A' in documents..."
oc exec $POD -- curl -s -X POST http://opensearch-service:9200/_all/_search \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "query": {
      "bool": {
        "should": [
          {"match": {"text": "S924"}},
          {"match": {"text": "9009-42A"}},
          {"match": {"metadata.doc_id": "S924"}}
        ]
      }
    },
    "aggs": {
      "by_index": {
        "terms": {
          "field": "_index",
          "size": 50
        }
      }
    }
  }' | python -m json.tool
echo ""
echo ""

echo "[3/3] Checking if there's an old 'power_s924' collection..."
oc exec $POD -- curl -s http://opensearch-service:9200/_cat/indices/power_s924,rag_power_s924,s924*?v 2>/dev/null
echo ""

echo "================================================================================"
echo "  Analysis"
echo "================================================================================"
echo ""
echo "This will show us if S924 data exists under a different collection name."
echo ""

# Made with Bob
