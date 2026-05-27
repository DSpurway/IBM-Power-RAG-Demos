#!/bin/bash

# Script to delete all OpenSearch collections
# After running this, use the frontend "Load All Documents" button to re-ingest

set -e

echo "=========================================="
echo "Delete All OpenSearch Collections"
echo "=========================================="
echo ""

# Get the backend route
BACKEND_ROUTE=$(oc get route rag-backend -o jsonpath='{.spec.host}')
BACKEND_URL="https://${BACKEND_ROUTE}"

echo "Backend URL: $BACKEND_URL"
echo ""

# Step 1: List all current collections
echo "Step 1: Listing current collections..."
echo "----------------------------------------"
SERVERS_JSON=$(curl -s "${BACKEND_URL}/api/servers")
echo "$SERVERS_JSON" | python3 -m json.tool
echo ""

# Extract server models
SERVER_MODELS=$(echo "$SERVERS_JSON" | python3 -c "import sys, json; data = json.load(sys.stdin); print(' '.join([s['model'] for s in data.get('servers', [])]))" 2>/dev/null || echo "")

if [ -z "$SERVER_MODELS" ]; then
    echo "No servers found. Nothing to delete."
    exit 0
fi

SERVER_COUNT=$(echo "$SERVER_MODELS" | wc -w)
echo "Found $SERVER_COUNT server collection(s) to delete"
echo ""

# Step 2: Confirm deletion
echo "Step 2: Confirm deletion"
echo "----------------------------------------"
echo "This will DELETE ALL $SERVER_COUNT collections:"
for server in $SERVER_MODELS; do
    echo "  - $server"
done
echo ""
echo "After deletion, you can use the frontend 'Load All Documents'"
echo "button to trigger bulk re-ingestion with improved chunking."
echo ""
read -p "Are you sure you want to DELETE ALL collections? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo ""
    echo "Aborted. No changes made."
    exit 0
fi

# Step 3: Delete all collections
echo ""
echo "Step 3: Deleting all collections..."
echo "----------------------------------------"

for server in $SERVER_MODELS; do
    echo "Deleting collection for: $server"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "${BACKEND_URL}/api/servers/${server}" -H "Content-Type: application/json")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "  ✓ Deleted successfully (HTTP $HTTP_CODE)"
    else
        echo "  ✗ Failed to delete (HTTP $HTTP_CODE)"
    fi
    
    sleep 0.5
done

echo ""
echo "Deletion complete!"
echo ""

# Step 4: Verify deletion
echo "Step 4: Verifying deletion..."
echo "----------------------------------------"
REMAINING=$(curl -s "${BACKEND_URL}/api/servers" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('servers', [])))" 2>/dev/null || echo "unknown")

if [ "$REMAINING" = "0" ]; then
    echo "✓ All collections deleted successfully!"
else
    echo "⚠ Warning: $REMAINING collection(s) still remain"
    curl -s "${BACKEND_URL}/api/servers" | python3 -m json.tool
fi

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Open the Sales Manual frontend in your browser"
echo "2. You should see: 'No servers indexed yet'"
echo "3. Click the 'Load All Documents' button"
echo "4. Bulk ingestion will start (takes several hours)"
echo "5. Monitor progress in the frontend or backend logs:"
echo "   oc logs -f deployment/rag-backend"
echo ""
echo "Note: Some servers may fail during ingestion."
echo "You can manually re-ingest failed servers later."
echo ""

# Made with Bob
