#!/bin/bash
# Test E980 Ingestion Workflow
# Complete workflow to test scraper, ingest E980, and validate results

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo "============================="
echo "  E980 Test Ingestion Workflow"
echo "============================="
echo ""
echo -e "${GRAY}Server: IBM Power System E980${NC}"
echo -e "${GRAY}MTM: 9080-M9S${NC}"
echo -e "${GRAY}Expected Collection: rag_mtm_9080_m9s${NC}"
echo -e "${GRAY}Sales Manual: https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s${NC}"
echo ""

# Configuration
SERVER_NAME="E980"
MTM="9080-M9S"
SALES_MANUAL_URL="https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s"
EXPECTED_COLLECTION="rag_mtm_9080_m9s"

# Step 1: Get scraper URL
echo -e "${YELLOW}Step 1: Getting Scraper Service URL${NC}"
echo "================================"
echo ""

if [ -f "scraper-url.txt" ]; then
    SCRAPER_URL=$(cat scraper-url.txt)
    echo -e "${GREEN}✓ Found scraper URL in scraper-url.txt${NC}"
    echo -e "${CYAN}  $SCRAPER_URL${NC}"
    echo ""
    read -p "Use this URL? (yes/no, default=yes): " use_saved
    
    if [ "$use_saved" = "no" ]; then
        SCRAPER_URL=""
    fi
fi

if [ -z "$SCRAPER_URL" ]; then
    echo -e "${YELLOW}Please provide the scraper service URL from IBM Code Engine:${NC}"
    echo -e "${GRAY}Example: https://ibm-docs-scraper.xxxxx.eu-gb.codeengine.appdomain.cloud${NC}"
    read -p "Scraper URL: " SCRAPER_URL
    
    if [ -z "$SCRAPER_URL" ]; then
        echo -e "${RED}Error: Scraper URL is required${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}Testing scraper service health...${NC}"

HEALTH_RESPONSE=$(curl -s -m 10 "$SCRAPER_URL/health" 2>&1)

if [ $? -eq 0 ] && echo "$HEALTH_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✓ Scraper service is healthy${NC}"
    echo -e "${GRAY}  Status: ok${NC}"
else
    echo -e "${RED}✗ Scraper service is not accessible${NC}"
    echo -e "${RED}  Response: $HEALTH_RESPONSE${NC}"
    echo ""
    echo -e "${YELLOW}Please ensure:${NC}"
    echo "  1. The scraper service is running in Code Engine"
    echo "  2. The URL is correct and accessible"
    exit 1
fi

# Step 2: Test scraping E980
echo ""
echo -e "${YELLOW}Step 2: Scraping E980 Sales Manual${NC}"
echo "==================================="
echo ""

echo -e "${YELLOW}Scraping $SALES_MANUAL_URL...${NC}"
echo -e "${GRAY}This may take 30-60 seconds (waiting for page to fully load)...${NC}"
echo ""

# Scraper uses GET with URL parameter (not POST with JSON)
# Add wait=15 parameter to give page time to load dynamic content
SCRAPE_RESPONSE=$(curl -s -m 120 -X GET "$SCRAPER_URL/scrape?url=$SALES_MANUAL_URL&wait=15" 2>&1)

if [ $? -ne 0 ] || [ -z "$SCRAPE_RESPONSE" ]; then
    echo -e "${RED}✗ Scraping failed${NC}"
    echo -e "${RED}  Error: $SCRAPE_RESPONSE${NC}"
    exit 1
fi

# Check if response contains content (without jq)
if echo "$SCRAPE_RESPONSE" | grep -q '"full_text"'; then
    echo -e "${GREEN}✓ Scraping completed successfully${NC}"
else
    echo -e "${RED}✗ Scraping failed - no content returned${NC}"
    echo "Response: $SCRAPE_RESPONSE"
    exit 1
fi

echo ""
echo -e "${CYAN}Scraped Content Summary:${NC}"

# Extract content length (rough estimate without jq)
# Scraper returns "full_text" field, not "content"
CONTENT=$(echo "$SCRAPE_RESPONSE" | sed -n 's/.*"full_text":"\(.*\)".*/\1/p')
CONTENT_LENGTH=${#CONTENT}
echo -e "${GRAY}  Total Length: ~$CONTENT_LENGTH characters${NC}"

# Check quality score
if echo "$SCRAPE_RESPONSE" | grep -q '"has_tables": true'; then
    echo -e "${GREEN}  ✓ Has Tables: true${NC}"
else
    echo -e "${YELLOW}  ⚠ Has Tables: false (page may not have loaded fully)${NC}"
fi

if [ $CONTENT_LENGTH -lt 1000 ]; then
    echo -e "${RED}  ⚠ WARNING: Content seems too short ($CONTENT_LENGTH chars)${NC}"
    echo -e "${YELLOW}  The scraper may not have retrieved the full page${NC}"
    echo ""
    read -p "Continue anyway? (yes/no): " continue_response
    if [ "$continue_response" != "yes" ]; then
        exit 1
    fi
fi

if echo "$CONTENT" | grep -q '|.*|'; then
    echo -e "${GRAY}  Has Tables: true${NC}"
else
    echo -e "${GRAY}  Has Tables: false${NC}"
fi

if echo "$CONTENT" | grep -q '#[A-Z0-9]\{4\}'; then
    echo -e "${GRAY}  Has Feature Codes: true${NC}"
else
    echo -e "${GRAY}  Has Feature Codes: false${NC}"
fi

if echo "$CONTENT" | grep -q "Product life cycle dates"; then
    echo -e "${GREEN}  ✓ Found 'Product life cycle dates' section${NC}"
else
    echo -e "${YELLOW}  ⚠ 'Product life cycle dates' section not found${NC}"
fi

# Save scraped content
echo "$SCRAPE_RESPONSE" > e980_scraped_response.json
echo ""
echo -e "${GRAY}  Saved to: e980_scraped_response.json${NC}"

# Step 3: Find rag-backend pod
echo ""
echo -e "${YELLOW}Step 3: Preparing Backend for Ingestion${NC}"
echo "========================================"
echo ""

POD=$(oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD" ]; then
    echo -e "${RED}✗ rag-backend pod not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found rag-backend pod: $POD${NC}"

# Step 4: Check if collection already exists
echo ""
echo -e "${YELLOW}Step 4: Checking Collection Status${NC}"
echo "==================================="
echo ""

CHECK_SCRIPT="
import os
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

collection_name = '$EXPECTED_COLLECTION'

if client.indices.exists(index=collection_name):
    doc_count = client.count(index=collection_name)['count']
    print('EXISTS:{}'.format(doc_count))
else:
    print('NOT_EXISTS')
"

RESULT=$(echo "$CHECK_SCRIPT" | oc exec -i $POD -- python 2>&1 | grep -E "EXISTS|NOT_EXISTS")

if echo "$RESULT" | grep -q "EXISTS:"; then
    DOC_COUNT=$(echo "$RESULT" | sed 's/EXISTS://')
    echo -e "${YELLOW}⚠ Collection already exists with $DOC_COUNT documents${NC}"
    echo ""
    read -p "Delete existing collection and re-ingest? (yes/no): " response
    
    if [ "$response" != "yes" ]; then
        echo -e "${YELLOW}Ingestion cancelled${NC}"
        exit 0
    fi
    
    echo ""
    echo -e "${YELLOW}Deleting existing collection...${NC}"
    
    DELETE_SCRIPT="
import os
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

client.indices.delete(index='$EXPECTED_COLLECTION')
print('DELETED')
"
    
    echo "$DELETE_SCRIPT" | oc exec -i $POD -- python 2>&1 > /dev/null
    echo -e "${GREEN}✓ Collection deleted${NC}"
else
    echo -e "${GREEN}✓ Collection does not exist (ready for fresh ingestion)${NC}"
fi

# Step 5: Ingest E980
echo ""
echo -e "${YELLOW}Step 5: Ingesting E980 into OpenSearch${NC}"
echo "======================================="
echo ""

echo -e "${YELLOW}Finding rag-backend service URL...${NC}"
# Fixed: Use correct route name
BACKEND_ROUTE=$(oc get route rag-backend -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -z "$BACKEND_ROUTE" ]; then
    echo -e "${RED}✗ rag-backend route not found${NC}"
    echo ""
    echo "Available routes:"
    oc get routes
    exit 1
fi

BACKEND_URL="https://$BACKEND_ROUTE"
echo -e "${GREEN}✓ Backend URL: $BACKEND_URL${NC}"
echo ""

echo -e "${YELLOW}Ingesting E980 sales manual...${NC}"
echo -e "${CYAN}This will:${NC}"
echo "  1. Parse scraped content with smart chunking"
echo "  2. Extract lifecycle table (preserved intact)"
echo "  3. Extract feature codes with metadata"
echo "  4. Create semantic chunks for RAG"
echo "  5. Generate embeddings for each chunk"
echo "  6. Store in OpenSearch collection: $EXPECTED_COLLECTION"
echo ""
echo -e "${GRAY}This may take 2-3 minutes...${NC}"
echo ""

# Send the scraped response to the ingestion endpoint
# The endpoint expects: success, url, page_title, full_text, server_model, mtm
INGEST_RESPONSE=$(curl -s -k -m 300 -X POST "$BACKEND_URL/ingest-scraped-content" \
    -H "Content-Type: application/json" \
    -d @e980_scraped_response.json 2>&1)

if [ $? -ne 0 ] || [ -z "$INGEST_RESPONSE" ]; then
    echo -e "${RED}✗ Ingestion failed${NC}"
    echo -e "${RED}  Error: $INGEST_RESPONSE${NC}"
    echo ""
    echo -e "${YELLOW}Check backend logs:${NC}"
    echo "  oc logs $POD"
    exit 1
fi

# Check for success without jq
if echo "$INGEST_RESPONSE" | grep -q '"success".*true'; then
    echo -e "${GREEN}✓ Ingestion completed successfully${NC}"
    echo ""
    echo -e "${CYAN}Ingestion Results:${NC}"
    
    # Extract key metrics from response (without jq)
    INDEXED=$(echo "$INGEST_RESPONSE" | sed -n 's/.*"indexed":\s*\([0-9]*\).*/\1/p')
    FAILED=$(echo "$INGEST_RESPONSE" | sed -n 's/.*"failed":\s*\([0-9]*\).*/\1/p')
    
    echo -e "${GRAY}  Chunks indexed: $INDEXED${NC}"
    echo -e "${GRAY}  Chunks failed: $FAILED${NC}"
    
    # Show chunk distribution if available
    if echo "$INGEST_RESPONSE" | grep -q '"chunk_distribution"'; then
        echo ""
        echo -e "${CYAN}Chunk Distribution by Type:${NC}"
        echo "$INGEST_RESPONSE" | grep -o '"chunk_distribution":{[^}]*}' | sed 's/[{}":]/ /g' | sed 's/chunk_distribution//'
    fi
    
    echo ""
    echo -e "${GRAY}Full Response:${NC}"
    echo "$INGEST_RESPONSE" | python -m json.tool 2>/dev/null || echo "$INGEST_RESPONSE"
else
    echo -e "${RED}✗ Ingestion failed${NC}"
    echo "Response: $INGEST_RESPONSE"
    echo ""
    echo -e "${YELLOW}Check backend logs:${NC}"
    echo "  oc logs $POD --tail=50"
    exit 1
fi

echo ""
echo "========================================"
echo -e "${CYAN}  E980 INGESTION COMPLETE${NC}"
echo "========================================"
echo ""
echo -e "${GRAY}Summary:${NC}"
echo -e "${GRAY}  Server: $SERVER_NAME (MTM: $MTM)${NC}"
echo -e "${GRAY}  Collection: $EXPECTED_COLLECTION${NC}"
echo -e "${GRAY}  Scraped Response: e980_scraped_response.json${NC}"
echo -e "${GRAY}  Chunks Indexed: $INDEXED${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Verify lifecycle table chunk:"
echo "     oc exec $POD -- python -c \"from opensearchpy import OpenSearch; c=OpenSearch([{'host':'opensearch-service','port':9200}],use_ssl=False); r=c.search(index='$EXPECTED_COLLECTION',body={'query':{'match':{'metadata.section_type':'lifecycle_table'}},'size':1}); print(r['hits']['hits'][0]['_source']['text'][:500] if r['hits']['hits'] else 'Not found')\""
echo ""
echo "  2. Check total document count:"
echo "     oc exec $POD -- python -c \"from opensearchpy import OpenSearch; c=OpenSearch([{'host':'opensearch-service','port':9200}],use_ssl=False); print(c.count(index='$EXPECTED_COLLECTION'))\""
echo ""
echo "  3. Test table lookup query via UI or API"
echo "  3. If good, proceed with other servers"
echo ""

# Made with Bob
