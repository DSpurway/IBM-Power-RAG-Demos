#!/bin/bash
# Complete E980 Reingest with Chunker Fix
# Commits changes, rebuilds backend, deletes old collection, and re-ingests

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

echo "========================================="
echo "  Complete E980 Reingest Workflow"
echo "========================================="
echo ""
echo -e "${CYAN}This will:${NC}"
echo "  1. Commit chunker changes to GitHub"
echo "  2. Rebuild rag-backend with updated code"
echo "  3. Delete existing E980 collection"
echo "  4. Re-ingest E980 with fixed chunker"
echo ""
read -p "Continue? (yes/no): " response

if [ "$response" != "yes" ]; then
    echo -e "${YELLOW}Cancelled${NC}"
    exit 0
fi

# Step 1: Commit changes to GitHub
echo ""
echo -e "${YELLOW}Step 1: Committing Changes to GitHub${NC}"
echo "======================================"
echo ""

cd C:/Users/029878866/EMEA-AI-SQUAD/RAG-with-Notebook

# Check if there are changes
if git diff --quiet sales_manual_chunker.py; then
    echo -e "${GRAY}No changes to commit${NC}"
else
    echo -e "${YELLOW}Committing chunker fix...${NC}"
    git add Part3-RAG-Sales-Manual/rag-backend/sales_manual_chunker.py
    git commit -m "Fix: Filter out dash-prefixed feature code list items

- Skip feature codes with dash prefix like '(#0004) -EMEA Bulk MES Indicator'
- These are list item references, not full descriptions
- Only extract full feature descriptions with complete metadata
- Eliminates ~50% duplicate feature code chunks"
    
    echo ""
    read -p "Push to GitHub? (yes/no): " push_response
    if [ "$push_response" = "yes" ]; then
        git push
        echo -e "${GREEN}✓ Changes pushed to GitHub${NC}"
    else
        echo -e "${YELLOW}⚠ Changes committed locally but not pushed${NC}"
    fi
fi

# Step 2: Rebuild backend
echo ""
echo -e "${YELLOW}Step 2: Rebuilding Backend${NC}"
echo "==========================="
echo ""

cd C:/Users/029878866/EMEA-AI-SQUAD/RAG-with-Notebook/Part3-RAG-Sales-Manual/rag-backend

echo -e "${YELLOW}Starting build from local directory...${NC}"
oc start-build rag-backend --from-dir=. --follow

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Build complete${NC}"
echo ""
echo -e "${YELLOW}Waiting for rollout...${NC}"
oc rollout status deployment/rag-backend

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Rollout failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Rollout complete${NC}"

# Step 3: Delete old collection
echo ""
echo -e "${YELLOW}Step 3: Deleting Old Collection${NC}"
echo "================================"
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

COLLECTION="rag_d0f9e9bb718684771b4eb639bf167a2d"

echo -e "${YELLOW}Deleting collection: $COLLECTION${NC}"

DELETE_SCRIPT="
import os
from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{'host': 'opensearch-service', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

if client.indices.exists(index='$COLLECTION'):
    client.indices.delete(index='$COLLECTION')
    print('DELETED')
else:
    print('NOT_EXISTS')
"

RESULT=$(echo "$DELETE_SCRIPT" | oc exec -i $POD -- python 2>&1)

if echo "$RESULT" | grep -q "DELETED"; then
    echo -e "${GREEN}✓ Collection deleted${NC}"
elif echo "$RESULT" | grep -q "NOT_EXISTS"; then
    echo -e "${GRAY}Collection did not exist${NC}"
else
    echo -e "${RED}✗ Error deleting collection${NC}"
    echo "$RESULT"
    exit 1
fi

# Step 4: Re-ingest E980
echo ""
echo -e "${YELLOW}Step 4: Re-ingesting E980${NC}"
echo "=========================="
echo ""

# Check if scraped file exists
if [ ! -f "e980_scraped_response.json" ]; then
    echo -e "${RED}✗ e980_scraped_response.json not found${NC}"
    echo ""
    echo "Running full ingestion with scraper..."
    ./test-e980-ingestion.sh
    exit $?
fi

echo -e "${GREEN}✓ Found e980_scraped_response.json${NC}"
echo ""

# Get backend URL
BACKEND_ROUTE=$(oc get route rag-backend -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -z "$BACKEND_ROUTE" ]; then
    echo -e "${RED}✗ rag-backend route not found${NC}"
    exit 1
fi

BACKEND_URL="https://$BACKEND_ROUTE"
echo -e "${CYAN}Backend URL: $BACKEND_URL${NC}"
echo ""
echo -e "${GRAY}Ingesting (this may take 2-3 minutes)...${NC}"

# Ingest
INGEST_RESPONSE=$(curl -s -k -m 300 -X POST "$BACKEND_URL/ingest-scraped-content" \
    -H "Content-Type: application/json" \
    -d @e980_scraped_response.json 2>&1)

if [ $? -ne 0 ] || [ -z "$INGEST_RESPONSE" ]; then
    echo -e "${RED}✗ Ingestion failed${NC}"
    echo -e "${RED}  Error: $INGEST_RESPONSE${NC}"
    exit 1
fi

if echo "$INGEST_RESPONSE" | grep -q '"success".*true'; then
    echo -e "${GREEN}✓ Ingestion completed successfully${NC}"
    echo ""
    
    INDEXED=$(echo "$INGEST_RESPONSE" | sed -n 's/.*"indexed":\s*\([0-9]*\).*/\1/p')
    echo -e "${CYAN}Chunks indexed: $INDEXED${NC}"
    
    if echo "$INGEST_RESPONSE" | grep -q '"chunk_distribution"'; then
        echo ""
        echo -e "${CYAN}Chunk Distribution:${NC}"
        echo "$INGEST_RESPONSE" | grep -o '"chunk_distribution":{[^}]*}'
    fi
else
    echo -e "${RED}✗ Ingestion failed${NC}"
    echo "$INGEST_RESPONSE"
    exit 1
fi

echo ""
echo "========================================="
echo -e "${GREEN}  REINGEST COMPLETE!${NC}"
echo "========================================="
echo ""
echo -e "${YELLOW}Verify results:${NC}"
echo "  ./inspect-e980-chunks.sh"
echo ""
echo -e "${GRAY}Expected: ~2,100 total chunks (half of previous 4,272)${NC}"
echo -e "${GRAY}Feature codes: ~1,017 (no dash-prefixed duplicates)${NC}"
echo ""

# Made with Bob
