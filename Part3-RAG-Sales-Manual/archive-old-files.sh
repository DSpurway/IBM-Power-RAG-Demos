#!/bin/bash

################################################################################
# Script: archive-old-files.sh
# Purpose: Archive old test scripts, debug files, and outdated documentation
# Usage: bash archive-old-files.sh
################################################################################

set -e

ARCHIVE_DIR="archive-$(date +%Y%m%d)"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Creating archive directory: $ARCHIVE_DIR"
mkdir -p "$ARCHIVE_DIR"

# Archive old test scripts (debugging/troubleshooting scripts no longer needed)
echo "Archiving old test and debug scripts..."
mv check-s924-collection.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv diagnose-s924-issue.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-s924-query-direct.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-s924-correct-url.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-s924-from-cluster.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-s924-query-fixed.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv check-all-indices.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv identify-mystery-index.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv compare-ui-vs-backend.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv monitor-s924-ingestion.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv check-scraper-health.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv check-e980-collection.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv cleanup-old-indices.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-intelligent-skip-windows.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-intelligent-skip.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-skip-logic.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-e980-manual-ingest.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv check-ingestion-results-simple.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv check-ingestion-results.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv check-bulk-status.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-bulk-ingestion-status.sh "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive PowerShell test scripts
echo "Archiving PowerShell test scripts..."
mv test-backend-direct.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-backend-health.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-collections-api.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-collections.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-lifecycle-query.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-s922-direct-ingest.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-s922-ingestion.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-e980-ingestion.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-e980-ingestion.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-ui-collections.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-ui-to-backend.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv trigger-bulk-ingestion.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv set-scraper-url.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive old deployment scripts (replaced by newer versions)
echo "Archiving old deployment scripts..."
mv deploy-fresh-cluster.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv deploy-fresh-cluster-git.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv deploy-status-fix.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv deploy-activation-ui.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv deploy-skip-logic-changes.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv deploy-skip-logic.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv fix-backend-labels.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv fix-routes.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv fix-routes.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv fix-ui-deployment.sh "$ARCHIVE_DIR/" 2>/dev/null || true
mv check-ui-status.sh "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive test data files
echo "Archiving test data files..."
mv backend-response.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv check-index.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv e980-ingest-payload.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv e980-ingestion-response.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv e980-scraped-content.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-query.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv test-response.json "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive old documentation (superseded by current docs)
echo "Archiving old documentation..."
mv ACTIVATION_DETAIL_VIEW_FEATURE.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv ACTIVATION_UI_IMPROVEMENTS.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv BUG_COMPLETED_COUNT.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv BULK_INGESTION_FIX.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv DEPLOY_ACTIVATION_FEATURES_COMPLETE.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv DEPLOY_STATUS_FIX_STEPS.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv DEPLOYMENT_FIXES.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv DEPLOYMENT_READY.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv FRESH_CLUSTER_DEPLOYMENT.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv FUTURE_ENHANCEMENTS.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv GRANITE_SERVICE_DEPLOYMENT.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv IBM_POWER_AI_FOUNDATION.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv OPENSEARCH_IMAGE_CRITICAL_FIX.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv SKIP_LOGIC_DOCUMENTATION.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv STATUS_DISPLAY_FIX.md "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive text files
echo "Archiving text files..."
mv "Name MTM and Sales Manual URL.txt" "$ARCHIVE_DIR/" 2>/dev/null || true
mv scraper-url.txt "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive old config files
echo "Archiving old config files..."
mv rag-backend-config.yaml "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive scraper-test directory if it exists
if [ -d "scraper-test" ]; then
    echo "Archiving scraper-test directory..."
    mv scraper-test "$ARCHIVE_DIR/" 2>/dev/null || true
fi

echo ""
echo "✅ Archive complete!"
echo ""
echo "Files moved to: $ARCHIVE_DIR"
echo ""
echo "📋 Files to KEEP (still needed):"
echo "  - README.md (main documentation)"
echo "  - DEPLOYMENT_GUIDE.md (deployment instructions)"
echo "  - QUICK_DEPLOY_REFERENCE.md (quick reference)"
echo "  - QUICK_START.md (getting started guide)"
echo "  - BULK_INGESTION_ENHANCEMENT.md (current feature docs)"
echo "  - DEPLOY_FRESH_POWER_CLUSTER.md (deployment guide)"
echo "  - deploy-fresh-cluster.sh (main deployment script)"
echo "  - deploy-ui.sh (UI deployment script)"
echo "  - setup-part3.sh (setup script)"
echo "  - carbon-rag-ui/ (UI application)"
echo "  - rag-backend/ (backend service)"
echo "  - granite-service/ (LLM service)"
echo "  - opensearch-deployment/ (vector DB)"
echo "  - llama-cpp-server/ (alternative LLM)"
echo "  - Agentic-Functions/ (agentic features)"
echo "  - Agentic-RAG/ (agentic RAG)"
echo ""
echo "To delete the archive after confirming everything works:"
echo "  rm -rf $ARCHIVE_DIR"
echo ""

# Made with Bob
