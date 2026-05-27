#!/bin/bash

# Cleanup Old MD5-Hashed Indices
# This script deletes all old rag_* indices that use MD5 hashing
# Run this AFTER deploying the new code but BEFORE bulk ingestion

set -e

echo "=========================================="
echo "Cleaning Up Old MD5-Hashed Indices"
echo "=========================================="
echo ""

# Get OpenSearch credentials from backend pod
echo "Getting OpenSearch credentials..."
BACKEND_POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')
OPENSEARCH_HOST=$(oc exec $BACKEND_POD -- printenv OPENSEARCH_HOST)
OPENSEARCH_USER=$(oc exec $BACKEND_POD -- printenv OPENSEARCH_USER)
OPENSEARCH_PASSWORD=$(oc exec $BACKEND_POD -- printenv OPENSEARCH_PASSWORD)

echo "OpenSearch Host: $OPENSEARCH_HOST"
echo ""

# List all current indices
echo "Current indices in OpenSearch:"
oc exec $BACKEND_POD -- curl -s -k -u "$OPENSEARCH_USER:$OPENSEARCH_PASSWORD" \
  "https://$OPENSEARCH_HOST/_cat/indices/rag_*?v&s=index"

echo ""
echo "=========================================="
echo "WARNING: This will delete ALL rag_* indices"
echo "=========================================="
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Deleting all rag_* indices..."

# Delete all rag_* indices
oc exec $BACKEND_POD -- curl -s -k -u "$OPENSEARCH_USER:$OPENSEARCH_PASSWORD" \
  -X DELETE "https://$OPENSEARCH_HOST/rag_*"

echo ""
echo "✓ All old indices deleted"
echo ""

# Verify deletion
echo "Remaining indices:"
oc exec $BACKEND_POD -- curl -s -k -u "$OPENSEARCH_USER:$OPENSEARCH_PASSWORD" \
  "https://$OPENSEARCH_HOST/_cat/indices/rag_*?v&s=index"

echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "Next step: Run bulk ingestion to create new readable indices"
echo ""

# Made with Bob
