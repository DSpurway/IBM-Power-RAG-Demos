#!/bin/bash
# Check if E980 collection exists and optionally delete it

set -e

BACKEND_URL="https://rag-backend-llm-on-techzone.apps.p1265.cecc.ihost.com"
COLLECTION_NAME="rag_mtm_9080_m9s"

echo "=== E980 Collection Check ==="
echo ""
echo "Checking for collection: $COLLECTION_NAME"
echo ""

# List all collections
echo "Fetching all collections..."
RESPONSE=$(curl -s "$BACKEND_URL/api/collections")

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

echo ""
echo "---"
echo ""

# Check if E980 collection exists
if echo "$RESPONSE" | grep -q "$COLLECTION_NAME"; then
    echo "✓ Collection '$COLLECTION_NAME' EXISTS"
    echo ""
    echo "Options:"
    echo "1. Delete and re-ingest (clean slate)"
    echo "2. Keep existing and add new data (may have duplicates)"
    echo ""
    read -p "Delete existing collection? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Deleting collection: $COLLECTION_NAME"
        
        DELETE_RESPONSE=$(curl -s -X DELETE "$BACKEND_URL/api/collections/$COLLECTION_NAME")
        
        if echo "$DELETE_RESPONSE" | grep -q '"success"[[:space:]]*:[[:space:]]*true'; then
            echo "✓ Collection deleted successfully"
        else
            echo "✗ Delete failed:"
            echo "$DELETE_RESPONSE"
            exit 1
        fi
    else
        echo "Keeping existing collection (new data will be added)"
    fi
else
    echo "✓ Collection '$COLLECTION_NAME' does NOT exist"
    echo "Ready for fresh ingestion"
fi

echo ""
echo "Ready to run: ./test-e980-ingestion.sh"

# Made with Bob
