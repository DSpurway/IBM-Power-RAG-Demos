#!/bin/bash
# Check current bulk ingestion status

BACKEND_URL="https://rag-backend-rag-demo.apps.p1265.cecc.ihost.com"

echo "=== Checking Bulk Ingestion Status ==="
echo ""

curl -X GET "${BACKEND_URL}/api/bulk-ingestion-status" -s -w "\n"

echo ""
echo "=== Explanation ==="
echo "If you see:"
echo "- 'in_progress': true  → Bulk ingestion is running"
echo "- 'in_progress': false → Bulk ingestion is idle"
echo "- 'skipped_count': X   → Number of servers skipped (NEW FEATURE)"
echo "- 'completed_count': Y → Number of servers re-ingested"
echo ""
echo "The intelligent skip feature is working if skipped_count > 0"

# Made with Bob
