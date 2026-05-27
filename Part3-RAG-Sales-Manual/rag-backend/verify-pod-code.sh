#!/bin/bash

# Verify the new pod has the fix

echo "Verifying Pod Code"
echo "=================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
    echo "No pod found yet. Wait a moment and try again."
    exit 1
fi

echo "Pod: $POD"
echo ""

echo "Checking for the fix in _find_section()..."
echo "==========================================="
echo ""

# Check if the fix is present
FIX_CHECK=$(oc exec $POD -- cat /app/sales_manual_chunker.py 2>/dev/null | grep -A 3 "def _find_section" | grep -c "Feature description")

if [ "$FIX_CHECK" -gt 0 ]; then
    echo "✓ FIX IS PRESENT in the pod!"
    echo ""
    echo "The code contains the check for 'Feature description'"
    echo ""
    oc exec $POD -- cat /app/sales_manual_chunker.py 2>/dev/null | grep -A 10 "def _find_section"
else
    echo "✗ FIX IS NOT PRESENT in the pod"
    echo ""
    echo "The pod is still running old code"
    echo ""
    oc exec $POD -- cat /app/sales_manual_chunker.py 2>/dev/null | grep -A 10 "def _find_section"
fi

echo ""
echo "==========================================="

# Made with Bob
