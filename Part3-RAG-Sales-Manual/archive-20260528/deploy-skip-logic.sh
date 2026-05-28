#!/bin/bash

# Deploy Skip Logic and Status Display Updates
# Complete deployment: GitHub sync → Rebuild from GitHub → Clean collections → Load All

echo "=========================================="
echo "Skip Logic Deployment Plan"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Commit and push changes to GitHub"
echo "  2. Rebuild backend from GitHub (not local)"
echo "  3. Rebuild frontend from GitHub (not local)"
echo "  4. Optionally clean existing collections"
echo "  5. Trigger 'Load All' from frontend"
echo ""
read -p "Continue? (y/n): " continue_deploy

if [ "$continue_deploy" != "y" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "=========================================="
echo "Step 1: Sync Changes to GitHub"
echo "=========================================="
echo ""

cd /c/Users/029878866/EMEA-AI-SQUAD/RAG-with-Notebook

echo "Adding documentation files..."
git add Part3-RAG-Sales-Manual/SKIP_LOGIC_DOCUMENTATION.md
git add Part3-RAG-Sales-Manual/BULK_INGESTION_ENHANCEMENT.md
git add Part3-RAG-Sales-Manual/BULK_INGESTION_FIX.md
git add Part3-RAG-Sales-Manual/STATUS_DISPLAY_FIX.md
git add Part3-RAG-Sales-Manual/*.sh

echo ""
echo "Committing changes..."
git commit -m "Add skip logic documentation and deployment scripts"

echo ""
echo "Pushing to GitHub..."
git push

echo ""
echo "✅ Changes synced to GitHub"
echo ""

# Step 2: Rebuild Backend from GitHub
echo "=========================================="
echo "Step 2: Rebuild Backend from GitHub"
echo "=========================================="
echo ""
echo "This will trigger a new build from the GitHub repository"
echo "NOT from local directory"
echo ""

cd Part3-RAG-Sales-Manual/rag-backend

echo "Starting backend build from GitHub..."
oc start-build rag-backend --follow

echo ""
echo "Restarting backend deployment..."
oc rollout restart deployment/rag-backend

echo ""
echo "Waiting for backend rollout..."
oc rollout status deployment/rag-backend

echo ""
echo "✅ Backend rebuilt and deployed from GitHub"
echo ""

# Step 3: Rebuild Frontend from GitHub
echo "=========================================="
echo "Step 3: Rebuild Frontend from GitHub"
echo "=========================================="
echo ""

cd ../carbon-rag-ui

echo "Starting frontend build from GitHub..."
oc start-build carbon-rag-ui --follow

echo ""
echo "Restarting frontend deployment..."
oc rollout restart deployment/carbon-rag-ui

echo ""
echo "Waiting for frontend rollout..."
oc rollout status deployment/carbon-rag-ui

echo ""
echo "✅ Frontend rebuilt and deployed from GitHub"
echo ""

# Step 4: Clean Existing Collections (Optional)
echo "=========================================="
echo "Step 4: Clean Existing Collections"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will delete all existing Sales Manual collections!"
echo "This ensures a clean slate for testing the skip logic."
echo ""
echo "After cleaning, the first 'Load All' will ingest all 26 servers."
echo "Subsequent 'Load All' runs will use skip logic."
echo ""
read -p "Clean existing collections? (y/n): " clean_collections

if [ "$clean_collections" = "y" ]; then
    echo ""
    echo "Cleaning collections..."
    
    # Get OpenSearch route
    OPENSEARCH_ROUTE=$(oc get route opensearch-service -o jsonpath='{.spec.host}')
    
    echo "OpenSearch URL: https://$OPENSEARCH_ROUTE"
    echo ""
    echo "Deleting rag_* indices..."
    
    # Delete all rag_* indices (Sales Manual collections)
    curl -X DELETE "https://$OPENSEARCH_ROUTE/rag_*" -k -u admin:admin
    
    echo ""
    echo "✅ Collections cleaned"
else
    echo ""
    echo "⏭️  Skipping collection cleanup"
    echo "Note: Skip logic will compare with existing collections"
fi

echo ""

# Step 5: Verify Deployments
echo "=========================================="
echo "Step 5: Verify Deployments"
echo "=========================================="
echo ""

echo "Backend pods:"
oc get pods | grep rag-backend

echo ""
echo "Frontend pods:"
oc get pods | grep carbon-rag-ui

echo ""
echo "Backend logs (last 10 lines):"
oc logs deployment/rag-backend --tail=10

echo ""

# Step 6: Trigger Load All
echo "=========================================="
echo "Step 6: Trigger 'Load All' Ingestion"
echo "=========================================="
echo ""

# Get backend route
BACKEND_ROUTE=$(oc get route rag-backend -o jsonpath='{.spec.host}')
BACKEND_URL="https://$BACKEND_ROUTE"

echo "Backend URL: $BACKEND_URL"
echo ""
echo "You can trigger 'Load All' in two ways:"
echo ""
echo "Option A: From the UI (Recommended)"
echo "  1. Open browser to the Sales Manual page"
echo "  2. Click 'Load All Documents' button"
echo "  3. Watch progress updates"
echo ""
echo "Option B: Via API"
echo "  curl -X POST $BACKEND_URL/api/start-bulk-ingestion \\"
echo "    -H 'Content-Type: application/json'"
echo ""
read -p "Trigger 'Load All' via API now? (y/n): " trigger_api

if [ "$trigger_api" = "y" ]; then
    echo ""
    echo "Starting bulk ingestion..."
    
    curl -X POST "$BACKEND_URL/api/start-bulk-ingestion" \
      -H "Content-Type: application/json" \
      -k
    
    echo ""
    echo ""
    echo "✅ Bulk ingestion started!"
    echo ""
    echo "Monitor progress:"
    echo "  curl $BACKEND_URL/api/bulk-ingestion-status -k | jq"
    echo ""
    echo "Or watch backend logs:"
    echo "  oc logs -f deployment/rag-backend | grep 'Bulk Ingestion'"
else
    echo ""
    echo "⏭️  Skipping API trigger"
    echo "Use the UI to trigger 'Load All' manually"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "📚 What was deployed:"
echo "  ✅ Documentation synced to GitHub"
echo "  ✅ Backend rebuilt from GitHub"
echo "  ✅ Frontend rebuilt from GitHub"
if [ "$clean_collections" = "y" ]; then
    echo "  ✅ Collections cleaned (fresh start)"
else
    echo "  ⏭️  Collections preserved (skip logic active)"
fi
echo ""
echo "🧪 Testing the Skip Logic:"
echo ""
echo "First Run (if collections cleaned):"
echo "  - All 26 servers will be ingested"
echo "  - Takes ~45-60 minutes"
echo "  - Each server gets content_hash stored"
echo ""
echo "Second Run (skip logic test):"
echo "  - Most servers will be skipped (unchanged)"
echo "  - Takes ~5-10 minutes"
echo "  - Only changed servers re-ingested"
echo ""
echo "🔍 Monitor Progress:"
echo "  Backend logs:  oc logs -f deployment/rag-backend | grep 'Bulk Ingestion'"
echo "  Status API:    curl $BACKEND_URL/api/bulk-ingestion-status -k | jq"
echo "  Browser:       Open DevTools Console (F12)"
echo ""
echo "📊 Expected Log Messages:"
echo "  ⏭️  Skipped 9009-42A (S924): unchanged"
echo "  🔄 Re-ingesting 9080-HEU (E1180): content_changed"
echo "  ✓ E1180 completed (47 documents)"
echo ""
echo "💡 Force Re-ingest All (if needed):"
echo "  curl -X POST $BACKEND_URL/api/start-bulk-ingestion \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"force\": true}' -k"
echo ""

# Made with Bob
