#!/bin/bash

# Check Bulk Ingestion Status
# Diagnose the current state of bulk ingestion on the backend

echo "========================================="
echo "Bulk Ingestion Status Check"
echo "========================================="
echo ""

# Get the backend pod name
BACKEND_POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

if [ -z "$BACKEND_POD" ]; then
    echo "❌ Error: Could not find rag-backend pod"
    exit 1
fi

echo "✅ Found backend pod: $BACKEND_POD"
echo ""

# Check if pod is running
POD_STATUS=$(oc get pod $BACKEND_POD -o jsonpath='{.status.phase}')
echo "📦 Pod status: $POD_STATUS"
echo ""

# Get bulk ingestion status from backend
echo "📊 Backend bulk ingestion state:"
echo "-----------------------------------"
STATUS_JSON=$(oc exec $BACKEND_POD -- curl -s http://localhost:8080/api/bulk-ingestion-status)
echo "$STATUS_JSON" | python3 -m json.tool

# Parse the status
IN_PROGRESS=$(echo "$STATUS_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('in_progress', False))")
COMPLETED_COUNT=$(echo "$STATUS_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('completed_count', 0))")
SKIPPED_COUNT=$(echo "$STATUS_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('skipped_count', 0))")
FAILED_COUNT=$(echo "$STATUS_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('failed_count', 0))")
TOTAL=$(echo "$STATUS_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total', 0))")
CURRENT_SERVER=$(echo "$STATUS_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('current_server', 'None'))")

echo ""
echo "========================================="
echo "Summary:"
echo "========================================="
echo "In Progress: $IN_PROGRESS"
echo "Current Server: $CURRENT_SERVER"
echo "Completed: $COMPLETED_COUNT"
echo "Skipped: $SKIPPED_COUNT"
echo "Failed: $FAILED_COUNT"
echo "Total: $TOTAL"
echo ""

# Check what's actually indexed in OpenSearch
echo "========================================="
echo "Actually Indexed Collections:"
echo "========================================="
COLLECTIONS_JSON=$(oc exec $BACKEND_POD -- curl -s http://localhost:8080/api/collections)
echo "$COLLECTIONS_JSON" | python3 -m json.tool
echo ""

# Provide recommendations
echo "========================================="
echo "Recommendations:"
echo "========================================="
echo ""

if [ "$IN_PROGRESS" = "True" ]; then
    echo "⚠️  Backend thinks ingestion is still in progress"
    echo ""
    echo "This could mean:"
    echo "1. The background thread is actually still running"
    echo "2. The thread crashed but didn't update the state"
    echo ""
    echo "Check backend logs to see if it's actually processing:"
    echo "  oc logs -f $BACKEND_POD --tail=50"
    echo ""
    echo "If it's stuck, you can restart the pod to reset the state:"
    echo "  oc delete pod $BACKEND_POD"
elif [ "$TOTAL" -gt 0 ]; then
    PROCESSED=$((COMPLETED_COUNT + SKIPPED_COUNT + FAILED_COUNT))
    echo "✅ Backend ingestion is NOT in progress"
    echo ""
    echo "Progress: $PROCESSED / $TOTAL servers processed"
    echo "  - Completed: $COMPLETED_COUNT"
    echo "  - Skipped: $SKIPPED_COUNT"
    echo "  - Failed: $FAILED_COUNT"
    echo ""
    if [ $PROCESSED -lt $TOTAL ]; then
        echo "⚠️  Ingestion appears to have stopped early"
        echo ""
        echo "To resume:"
        echo "1. Refresh your browser"
        echo "2. Click 'Refresh Status' in the UI"
        echo "3. Click 'Load All Documents' again"
        echo "   (It will skip already-indexed servers)"
    else
        echo "✅ All servers have been processed!"
        echo ""
        echo "Just refresh your browser to see the updated status."
    fi
else
    echo "ℹ️  No bulk ingestion has been started yet"
    echo ""
    echo "You can start it from the UI by clicking 'Load All Documents'"
fi

echo ""

# Made with Bob
