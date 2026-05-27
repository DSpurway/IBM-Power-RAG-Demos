#!/bin/bash

# Check Bulk Ingestion Results (No jq required, uses oc exec)
# Shows what was actually ingested

echo "=========================================="
echo "Bulk Ingestion Results Analysis"
echo "=========================================="
echo ""

# Get backend route
BACKEND_ROUTE=$(oc get route rag-backend -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -z "$BACKEND_ROUTE" ]; then
    echo "❌ Could not get backend route"
    echo "Make sure you're logged into OpenShift"
    exit 1
fi

BACKEND_URL="https://$BACKEND_ROUTE"

echo "Backend URL: $BACKEND_URL"
echo ""

# Get bulk ingestion status
echo "=========================================="
echo "Bulk Ingestion Status (Raw JSON)"
echo "=========================================="
echo ""

curl -s "$BACKEND_URL/api/bulk-ingestion-status" -k

echo ""
echo ""

# Get OpenSearch indices using oc exec
echo "=========================================="
echo "OpenSearch Indices (via oc exec)"
echo "=========================================="
echo ""

# Get backend pod name
BACKEND_POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$BACKEND_POD" ]; then
    echo "❌ Could not find backend pod"
else
    echo "Using backend pod: $BACKEND_POD"
    echo ""
    echo "Listing all rag_* indices:"
    echo ""
    
    # Query OpenSearch from inside the cluster
    oc exec "$BACKEND_POD" -- curl -s "http://opensearch-service:9200/_cat/indices/rag_*?v&h=index,docs.count,store.size&s=index" -u admin:admin
    
    echo ""
    echo ""
    echo "Total rag_* indices:"
    oc exec "$BACKEND_POD" -- curl -s "http://opensearch-service:9200/_cat/indices/rag_*?h=index" -u admin:admin | wc -l
fi

echo ""
echo ""
echo "=========================================="
echo "Backend Logs (Last 50 lines)"
echo "=========================================="
echo ""
echo "Looking for completion message..."
echo ""

oc logs deployment/rag-backend --tail=50 | grep -E "Bulk Ingestion.*Complete|succeeded|skipped|failed"

echo ""
echo ""
echo "=========================================="
echo "Analysis Guide"
echo "=========================================="
echo ""
echo "From the JSON output above, check:"
echo ""
echo "  completed_count: Number of servers successfully ingested"
echo "  skipped_count:   Number of servers skipped (unchanged)"
echo "  failed_count:    Number of servers that failed"
echo "  total:           Total servers in list"
echo ""
echo "Expected for first run:"
echo "  - completed_count: 26"
echo "  - skipped_count: 0"
echo "  - failed_count: 0"
echo ""
echo "If completed_count is 46:"
echo "  1. Check the 'completed' array for duplicate MTMs"
echo "  2. May indicate:"
echo "     - Multiple 'Load All' runs overlapping"
echo "     - Server list includes variants (S924, S924-G, etc.)"
echo "     - Bug in completion tracking"
echo ""
echo "To see full server list, run:"
echo "  curl https://$BACKEND_URL/api/bulk-ingestion-status -k | grep -A 100 'completed'"
echo ""

# Made with Bob
