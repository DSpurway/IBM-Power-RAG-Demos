#!/bin/bash
# Monitor S924 ingestion progress

POD=$(oc get pod -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

echo "================================================================================"
echo "  Monitoring S924 Ingestion Progress"
echo "================================================================================"
echo ""
echo "Backend pod: $POD"
echo ""
echo "Watching logs for S924 and 9009-42A mentions..."
echo "Press Ctrl+C to stop"
echo ""
echo "================================================================================"
echo ""

# Follow logs and filter for S924-related entries
oc logs -f $POD 2>&1 | grep --line-buffered -i "s924\|9009-42\|bulk.*progress\|ingestion.*complete"

# Made with Bob
