#!/bin/bash

# Check what code is actually running in the pod

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

echo "Checking code in pod: $POD"
echo ""
echo "Looking for the fix in _find_section():"
echo "========================================"

oc exec $POD -- grep -A 5 "def _find_section" /app/sales_manual_chunker.py | head -20

# Made with Bob
