#!/bin/bash

################################################################################
# Script: archive-old-files-root.sh
# Purpose: Archive old files from RAG-with-Notebook root directory
# Usage: bash archive-old-files-root.sh
################################################################################

set -e

ARCHIVE_DIR="archive-root-$(date +%Y%m%d)"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Creating archive directory: $ARCHIVE_DIR"
mkdir -p "$ARCHIVE_DIR"

# Archive old summary/documentation files (superseded)
echo "Archiving old documentation and summary files..."
mv BACKEND_CONSOLIDATION_SUMMARY.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv CARBON_UI_SUMMARY.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv DEPLOY_MANUAL_STEPS.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv DEPLOYMENT_WALKTHROUGH.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv DUAL_MODEL_IMPLEMENTATION.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv DYNAMIC_PAGES_FEATURE_SUMMARY.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv IMPROVEMENTS_SUMMARY.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv OPENSEARCH_DEPLOYMENT_GUIDE.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv OPENSEARCH_MIGRATION.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv POWERSHELL_SYNTAX_GUIDE.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv WATSON_ASSISTANT_AND_BUG_FIX_SUMMARY.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv WATSON_INTEGRATION_COMPLETE.md "$ARCHIVE_DIR/" 2>/dev/null || true
mv README.old.md "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive test response JSON files
echo "Archiving test response files..."
mv granite_route_test_response.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv granite_test_response_new.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv watson_response_20260507_155857.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv watson_response_20260507_155859.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv watson_response_20260507_155900.json "$ARCHIVE_DIR/" 2>/dev/null || true
mv watson_response_20260507_155902.json "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive old deployment scripts
echo "Archiving old deployment scripts..."
mv commit-and-deploy.ps1 "$ARCHIVE_DIR/" 2>/dev/null || true
mv commit-bulk-ingestion-enhancement.sh "$ARCHIVE_DIR/" 2>/dev/null || true

# Archive Further-work directory if it exists
if [ -d "Further-work" ]; then
    echo "Archiving Further-work directory..."
    mv Further-work "$ARCHIVE_DIR/" 2>/dev/null || true
fi

echo ""
echo "✅ Root directory archive complete!"
echo ""
echo "Files moved to: $ARCHIVE_DIR"
echo ""
echo "📋 Files to KEEP (still needed):"
echo "  - README.md (main project documentation)"
echo "  - QUICK_START.md (getting started guide)"
echo "  - AGENTS.md (agent documentation)"
echo "  - LICENSE (project license)"
echo "  - RAG.ipynb (Jupyter notebook)"
echo "  - .gitignore (git configuration)"
echo "  - .roomodes (Roo configuration)"
echo "  - .bob/ (Bob AI assistant config)"
echo "  - images/ (documentation images)"
echo "  - Part1-Deploy-LLM/ (Part 1 content)"
echo "  - Part2-RAG/ (Part 2 content)"
echo "  - Part3-RAG-Sales-Manual/ (Part 3 content - main demo)"
echo ""
echo "To delete the archive after confirming everything works:"
echo "  rm -rf $ARCHIVE_DIR"
echo ""

# Made with Bob
