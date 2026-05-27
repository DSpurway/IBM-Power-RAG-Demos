#!/bin/bash

# Hotfix: Directly copy the fixed file into the running pod

echo "Hotfix Deployment"
echo "================="
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
    echo "✗ No pod found"
    exit 1
fi

echo "Pod: $POD"
echo ""

echo "Step 1: Copying fixed file to pod..."
cat sales_manual_chunker.py | oc exec -i $POD -- tee /app/sales_manual_chunker.py > /dev/null
echo "✓ File copied"
echo ""

echo "Step 2: Verifying fix is present..."
FIX_CHECK=$(oc exec $POD -- cat /app/sales_manual_chunker.py 2>/dev/null | grep -A 3 "def _find_section" | grep -c "Feature description")

if [ "$FIX_CHECK" -gt 0 ]; then
    echo "✓ FIX IS NOW PRESENT in the pod!"
    echo ""
    echo "Showing the fixed code:"
    oc exec $POD -- cat /app/sales_manual_chunker.py 2>/dev/null | grep -A 12 "def _find_section"
else
    echo "✗ Fix still not present - something went wrong"
    exit 1
fi

echo ""
echo "================="
echo "✓ Hotfix Complete"
echo "================="
echo ""
echo "The pod now has the fixed code."
echo "You can now reingest E980 and it should work correctly."
echo ""
echo "Note: This is a temporary fix. The next pod restart will revert to the image."
echo "We need to figure out why the build process isn't working."

# Made with Bob
