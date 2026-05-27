#!/bin/bash
# Test E980 Ingestion - Complete End-to-End Test
# Uses scraped content from Code Engine scraper service

set -e
CURL_INSECURE="${CURL_INSECURE:-true}"

echo "=== E980 Sales Manual Ingestion Test ==="
echo ""

# Configuration
BACKEND_URL="https://rag-backend-llm-on-techzone.apps.p1265.cecc.ihost.com"
E980_URL="https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s"
E980_MTM="9080-M9S"
E980_NAME="IBM Power System E980"
E980_SERVER_MODEL="E980"

# Step 1: Get scraper URL
echo "Step 1: Getting scraper service URL..."
SCRAPER_URL_FILE="rag-backend/scraper-url.txt"

if [ -f "$SCRAPER_URL_FILE" ]; then
    SCRAPER_URL=$(cat "$SCRAPER_URL_FILE" | tr -d '\r\n')
    echo "✓ Using cached scraper URL: $SCRAPER_URL"
else
    echo "✗ Scraper URL not found at $SCRAPER_URL_FILE"
    echo "Run: cd rag-backend && bash get-scraper-url-simple.sh"
    exit 1
fi

# Step 2: Scrape E980 content
echo ""
echo "Step 2: Scraping E980 Sales Manual..."
echo "URL: $E980_URL"

ENCODED_URL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$E980_URL'))")
SCRAPE_URL="$SCRAPER_URL/scrape?url=$ENCODED_URL"

echo "Calling scraper (this may take 15-20 seconds)..."

CURL_SSL_ARGS=()
if [ "$CURL_INSECURE" = "true" ]; then
    CURL_SSL_ARGS=(-k)
fi

SCRAPE_RESPONSE=$(curl "${CURL_SSL_ARGS[@]}" -s -X GET "$SCRAPE_URL" --max-time 60)

# Check if scraping was successful
SUCCESS=$(echo "$SCRAPE_RESPONSE" | grep -o '"success"[[:space:]]*:[[:space:]]*true' || echo "")

if [ -z "$SUCCESS" ]; then
    echo "✗ Scraping failed"
    echo "$SCRAPE_RESPONSE"
    exit 1
fi

# Extract content length
CONTENT_LENGTH=$(echo "$SCRAPE_RESPONSE" | grep -o '"full_text"[[:space:]]*:[[:space:]]*"[^"]*"' | wc -c)

echo "✓ Scraping successful!"
echo "  Content length: ~$CONTENT_LENGTH characters"

# Save scraped content
echo "$SCRAPE_RESPONSE" > e980-scraped-content.json
echo "  Saved to: e980-scraped-content.json"

# Step 3: Ingest into backend
echo ""
echo "Step 3: Ingesting into RAG backend..."
echo "Backend: $BACKEND_URL"
echo "Collection: rag_mtm_9080_m9s"

# Transform scraper output to backend contract
python3 - <<PY
import json

with open("e980-scraped-content.json", "r", encoding="utf-8") as f:
    scraped = json.load(f)

payload = {
    "success": True,
    "url": "${E980_URL}",
    "page_title": "${E980_NAME}",
    "full_text": scraped.get("full_text", ""),
    "server_model": "${E980_SERVER_MODEL}",
    "mtm": "${E980_MTM}",
    "content_length": len(scraped.get("full_text", "")),
}
with open("e980-ingest-payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
PY

echo "  Prepared payload: e980-ingest-payload.json"

# Send transformed content to backend
echo "Sending to backend (this may take 30-60 seconds)..."

INGEST_RESPONSE=$(curl "${CURL_SSL_ARGS[@]}" -s -X POST "$BACKEND_URL/ingest-scraped-content" \
    -H "Content-Type: application/json" \
    -d @e980-ingest-payload.json \
    --max-time 120)

# Check if ingestion was successful
INGEST_SUCCESS=$(echo "$INGEST_RESPONSE" | grep -o '"success"[[:space:]]*:[[:space:]]*true' || echo "")

if [ -z "$INGEST_SUCCESS" ]; then
    echo "✗ Ingestion failed"
    echo "$INGEST_RESPONSE"
    exit 1
fi

echo "✓ Ingestion successful!"

# Extract actual backend response fields
CHUNKS_INDEXED=$(echo "$INGEST_RESPONSE" | grep -o '"indexed"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*$')
CHUNKS_FAILED=$(echo "$INGEST_RESPONSE" | grep -o '"failed"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*$')
COLLECTION_NAME=$(echo "$INGEST_RESPONSE" | grep -o '"collection"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"collection"[[:space:]]*:[[:space:]]*"\([^"]*\)"/\1/')

echo "  Chunks indexed: $CHUNKS_INDEXED"
echo "  Chunks failed: $CHUNKS_FAILED"
echo "  Collection: $COLLECTION_NAME"

# Save ingestion response
echo "$INGEST_RESPONSE" > e980-ingestion-response.json
echo "  Saved to: e980-ingestion-response.json"

# Step 4: Display chunk distribution
echo ""
echo "Chunk Distribution:"
echo "$INGEST_RESPONSE" | grep -o '"chunk_distribution"[[:space:]]*:[[:space:]]*{[^}]*}' | sed 's/[{}"]//g' | sed 's/,/\n/g' | sed 's/^/  /'

# Step 5: Validate ingestion
echo ""
echo "Step 4: Validating ingestion quality..."

# Check for lifecycle table
if echo "$SCRAPE_RESPONSE" | grep -q "Product life cycle dates"; then
    echo "✓ Lifecycle table found in source"
else
    echo "✗ WARNING: No lifecycle table in source"
fi

# Check for activation features
ACTIVATION_COUNT=$(echo "$SCRAPE_RESPONSE" | grep -io '(#[A-Z0-9]\{4\})[^)]*activation' | wc -l)
if [ "$ACTIVATION_COUNT" -gt 0 ]; then
    echo "✓ Found $ACTIVATION_COUNT activation features"
else
    echo "⚠ No activation features found"
fi

# Check for mixed MTM contamination
CONTAMINATED=0
for MTM in "9043-MRX" "9080-HEX" "9009-42A" "9009-22A"; do
    if echo "$SCRAPE_RESPONSE" | grep -q "$MTM"; then
        echo "✗ WARNING: Found reference to other MTM: $MTM"
        CONTAMINATED=1
    fi
done

if [ "$CONTAMINATED" -eq 0 ]; then
    echo "✓ No mixed MTM contamination detected"
fi

echo ""
echo "=== E980 Ingestion Complete ==="
echo ""
echo "Next steps:"
echo "1. Query lifecycle: test-e980-lifecycle-query.sh"
echo "2. Query activations: test-e980-activation-query.sh"
echo "3. Inspect chunks: cat e980-ingestion-response.json | jq"

# Made with Bob
