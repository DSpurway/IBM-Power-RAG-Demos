#!/bin/bash

# Check Bulk Ingestion Results
# Shows what was actually ingested and identifies any duplicates

echo "=========================================="
echo "Bulk Ingestion Results Analysis"
echo "=========================================="
echo ""

# Get backend route
BACKEND_ROUTE=$(oc get route rag-backend -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -z "$BACKEND_ROUTE" ]; then
    echo "❌ Could not get backend route"
    exit 1
fi

BACKEND_URL="https://$BACKEND_ROUTE"

echo "Backend URL: $BACKEND_URL"
echo ""

# Get bulk ingestion status
echo "=========================================="
echo "Final Bulk Ingestion Status"
echo "=========================================="
echo ""

STATUS=$(curl -s "$BACKEND_URL/api/bulk-ingestion-status" -k)
echo "$STATUS" | jq '.'

echo ""

# Extract counts
COMPLETED=$(echo "$STATUS" | jq -r '.completed_count // 0')
SKIPPED=$(echo "$STATUS" | jq -r '.skipped_count // 0')
FAILED=$(echo "$STATUS" | jq -r '.failed_count // 0')
TOTAL=$(echo "$STATUS" | jq -r '.total // 0')

echo "Summary:"
echo "  Completed: $COMPLETED"
echo "  Skipped:   $SKIPPED"
echo "  Failed:    $FAILED"
echo "  Total:     $TOTAL"
echo ""

# List completed servers
echo "=========================================="
echo "Completed Servers"
echo "=========================================="
echo ""
echo "$STATUS" | jq -r '.completed[]?' | sort

echo ""

# List skipped servers
echo "=========================================="
echo "Skipped Servers"
echo "=========================================="
echo ""
echo "$STATUS" | jq -r '.skipped[]?.mtm?' | sort

echo ""

# List failed servers
echo "=========================================="
echo "Failed Servers"
echo "=========================================="
echo ""
echo "$STATUS" | jq -r '.failed[]?' | sort

echo ""

# Check for duplicates in completed list
echo "=========================================="
echo "Checking for Duplicates"
echo "=========================================="
echo ""

COMPLETED_LIST=$(echo "$STATUS" | jq -r '.completed[]?' | sort)
UNIQUE_COUNT=$(echo "$COMPLETED_LIST" | sort -u | wc -l)
TOTAL_COUNT=$(echo "$COMPLETED_LIST" | wc -l)

if [ "$UNIQUE_COUNT" -ne "$TOTAL_COUNT" ]; then
    echo "⚠️  WARNING: Duplicates detected!"
    echo "  Unique servers: $UNIQUE_COUNT"
    echo "  Total entries:  $TOTAL_COUNT"
    echo ""
    echo "Duplicate servers:"
    echo "$COMPLETED_LIST" | sort | uniq -d
else
    echo "✅ No duplicates found"
    echo "  All $UNIQUE_COUNT servers are unique"
fi

echo ""

# Check OpenSearch indices
echo "=========================================="
echo "OpenSearch Indices"
echo "=========================================="
echo ""

OPENSEARCH_ROUTE=$(oc get route opensearch-service -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -z "$OPENSEARCH_ROUTE" ]; then
    echo "❌ Could not get OpenSearch route"
else
    echo "Listing all rag_* indices:"
    echo ""
    curl -s "https://$OPENSEARCH_ROUTE/_cat/indices/rag_*?v&h=index,docs.count,store.size&s=index" -k -u admin:admin
    
    echo ""
    echo ""
    echo "Total indices:"
    INDEX_COUNT=$(curl -s "https://$OPENSEARCH_ROUTE/_cat/indices/rag_*?h=index" -k -u admin:admin | wc -l)
    echo "  $INDEX_COUNT rag_* indices found"
fi

echo ""

# Expected server count
echo "=========================================="
echo "Expected vs Actual"
echo "=========================================="
echo ""
echo "Expected servers: 26"
echo "Completed:        $COMPLETED"
echo "Skipped:          $SKIPPED"
echo "Failed:           $FAILED"
echo ""

if [ "$COMPLETED" -gt 26 ]; then
    echo "⚠️  More servers completed than expected!"
    echo "This could indicate:"
    echo "  - Duplicate processing"
    echo "  - Multiple 'Load All' runs overlapping"
    echo "  - Server list includes variants (e.g., S924 and S924-G)"
elif [ "$COMPLETED" -lt 26 ]; then
    echo "⚠️  Fewer servers completed than expected"
    echo "Check failed list above"
else
    echo "✅ Server count matches expected (26)"
fi

echo ""
echo "=========================================="
echo "Analysis Complete"
echo "=========================================="
echo ""

# Made with Bob
