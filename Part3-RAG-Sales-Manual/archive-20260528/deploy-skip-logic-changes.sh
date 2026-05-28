#!/bin/bash

# Deploy Skip Logic and MD5 Removal Changes
# This script commits changes and rebuilds backend and frontend services

set -e

echo "=========================================="
echo "Deploying Skip Logic Enhancement"
echo "=========================================="
echo ""

# Step 1: Commit changes to Git
echo "Step 1: Committing changes to Git..."
cd ~/EMEA-AI-SQUAD/RAG-with-Notebook

git add Part3-RAG-Sales-Manual/rag-backend/app.py
git add Part3-RAG-Sales-Manual/rag-backend/table_lookup_service.py
git add Part3-RAG-Sales-Manual/rag-backend/sales_manual_chunker.py
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/page.js
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/api/bulk-ingest/route.js

git commit -m "feat: Remove MD5 hashing + intelligent skip logic with content hash detection

- Remove MD5 index name hashing, use readable names (rag_mtm_9009_42a)
- Add intelligent skip logic to avoid re-ingesting unchanged servers
- Fix content hash query to check metadata.content_hash
- Fix 400 Bad Request error with silent JSON parsing
- Add skip reasons: unchanged, content_changed, index_missing, etc.
- Update frontend to display skipped servers in progress UI"

git push origin main

echo ""
echo "✓ Changes committed and pushed to GitHub"
echo ""

# Step 2: Rebuild backend from Git
echo "Step 2: Rebuilding backend from Git..."
oc start-build rag-backend --follow

echo ""
echo "✓ Backend rebuild complete"
echo ""

# Step 3: Rebuild frontend from Git
echo "Step 3: Rebuilding frontend from Git..."
oc start-build carbon-rag-ui --follow

echo ""
echo "✓ Frontend rebuild complete"
echo ""

# Step 4: Wait for deployments to roll out
echo "Step 4: Waiting for deployments to stabilize..."
oc rollout status deployment/rag-backend
oc rollout status deployment/carbon-rag-ui

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Delete old MD5-hashed indices in OpenSearch"
echo "2. Run bulk ingestion to create new readable indices"
echo "3. Run bulk ingestion again to test skip logic"
echo ""
echo "Expected behavior:"
echo "- First run: Creates all 26 collections (45-60 min)"
echo "- Second run: Skips ~24 unchanged servers (5-10 min)"
echo ""

# Made with Bob
