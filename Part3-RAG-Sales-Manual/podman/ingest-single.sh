#!/bin/bash
# =============================================================================
# ingest-single.sh — Test chunking + ingestion for ONE Sales Manual
# =============================================================================
# Run this after the stack is up to validate chunking before bulk ingestion.
# Inspect the returned chunks carefully before running bulk ingestion.
#
# Usage:
#   ./ingest-single.sh <mtm> <url>
#
# Example (IBM Power E980):
#   ./ingest-single.sh "9080-M9S" \
#     "https://www.ibm.com/docs/en/power10?topic=overview-power-e980"
#
# The script:
#   1. Posts the URL to the RAG backend /ingest endpoint
#   2. Pretty-prints the response (number of chunks, chunk types, sample text)
#   3. Immediately queries OpenSearch to show what was stored
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info() { echo -e "  ${BLUE}ℹ${NC}  $*"; }
ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✗${NC}  $*"; exit 1; }

# ── Args ──────────────────────────────────────────────────────────────────────
MTM="${1:-}"
URL="${2:-}"

if [[ -z "${MTM}" || -z "${URL}" ]]; then
    echo ""
    echo -e "${BOLD}Usage:${NC}  ./ingest-single.sh <mtm> <url>"
    echo ""
    echo "  Example:"
    echo '    ./ingest-single.sh "9080-M9S" \'
    echo '      "https://www.ibm.com/docs/en/power10?topic=overview-power-e980"'
    echo ""
    echo "  The MTM is used as the OpenSearch collection name."
    echo "  Check available MTMs in:"
    echo "    ../archive-20260528/Name\ MTM\ and\ Sales\ Manual\ URL.txt"
    echo ""
    exit 1
fi

BACKEND_URL="${BACKEND_URL:-http://localhost:8080}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BOLD}${CYAN}  RAG Demo — Single Sales Manual Ingestion Test${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "MTM:     ${MTM}"
info "URL:     ${URL}"
info "Backend: ${BACKEND_URL}"
echo ""

# ── 1. Check backend is up ────────────────────────────────────────────────────
info "Checking RAG backend health…"
if ! curl -sf "${BACKEND_URL}/health" > /dev/null; then
    err "RAG backend not reachable at ${BACKEND_URL}. Is the stack running? (./manage.sh status)"
fi
ok "Backend is healthy"
echo ""

# ── 2. POST to /ingest ────────────────────────────────────────────────────────
PAYLOAD=$(cat <<EOF
{
  "url": "${URL}",
  "mtm": "${MTM}",
  "force_reingest": true
}
EOF
)

echo -e "${BOLD}Step 1: Sending ingestion request…${NC}"
info "POST ${BACKEND_URL}/ingest"
echo ""

RESPONSE_FILE=$(mktemp /tmp/ingest-response-XXXXXX.json)
HTTP_STATUS=$(curl -s -o "${RESPONSE_FILE}" -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "${PAYLOAD}" \
    "${BACKEND_URL}/ingest")

if [[ "${HTTP_STATUS}" -ne 200 ]]; then
    err "Ingestion request failed — HTTP ${HTTP_STATUS}"
    echo ""
    echo "Response body:"
    cat "${RESPONSE_FILE}"
    rm -f "${RESPONSE_FILE}"
    exit 1
fi

ok "Ingestion request accepted (HTTP 200)"
echo ""

# ── 3. Parse and display chunk summary ───────────────────────────────────────
echo -e "${BOLD}Step 2: Chunk summary${NC}"
echo ""

TOTAL=$(python3 -c "
import json, sys
d = json.load(open('${RESPONSE_FILE}'))
chunks = d.get('chunks', d.get('documents', []))
print(len(chunks))
" 2>/dev/null || echo "?")

info "Total chunks created: ${TOTAL}"

python3 - <<PYEOF
import json
from collections import Counter

data = json.load(open("${RESPONSE_FILE}"))
chunks = data.get("chunks", data.get("documents", []))

types = Counter(
    c.get("metadata", {}).get("section_type", "unknown")
    for c in chunks
)
print("\n  Chunk types:")
for t, n in sorted(types.items()):
    print(f"    {n:3d}  {t}")
PYEOF

echo ""

# Show first chunk of each type as a sample
echo -e "${BOLD}Step 3: Sample chunks (first of each type)${NC}"
echo ""

python3 - <<PYEOF
import json

CYAN  = "\033[0;36m"
BOLD  = "\033[1m"
NC    = "\033[0m"

data = json.load(open("${RESPONSE_FILE}"))
chunks = data.get("chunks", data.get("documents", []))

seen_types = set()
for c in chunks:
    stype = c.get("metadata", {}).get("section_type", "unknown")
    if stype in seen_types:
        continue
    seen_types.add(stype)

    meta  = c.get("metadata", {})
    text  = c.get("text", c.get("page_content", ""))
    title = meta.get("section_title", "")
    feat  = meta.get("feature_code", "")

    print(f"{BOLD}{CYAN}  ── {stype} ──{NC}")
    if title:
        print(f"  Title:  {title}")
    if feat:
        print(f"  Feature code: #{feat}")
    preview = " ".join(text.split())[:300]
    print(f"  Text preview:\n    {preview}…")
    print()
PYEOF

rm -f "${RESPONSE_FILE}"

# ── 4. Spot-check OpenSearch directly ────────────────────────────────────────
echo -e "${BOLD}Step 4: OpenSearch doc count for ${MTM}${NC}"
echo ""

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"

COLLECTION_INFO=$(curl -sf "${BACKEND_URL}/collections" 2>/dev/null || echo "{}")

COLLECTION=$(python3 -c "
import json, sys
data = json.loads('''${COLLECTION_INFO}''')
colls = data.get('collections', [])
for c in colls:
    if c.get('name','').upper() == '${MTM}'.upper() or '${MTM}'.upper() in c.get('name','').upper():
        print(c.get('index_name', c.get('name', '')))
        sys.exit(0)
print('')
" 2>/dev/null)

if [[ -n "${COLLECTION}" ]]; then
    COUNT=$(curl -sf "${OPENSEARCH_URL}/${COLLECTION}/_count" 2>/dev/null \
        | python3 -c "import json,sys; print(json.load(sys.stdin).get('count','?'))" 2>/dev/null \
        || echo "?")
    ok "OpenSearch index '${COLLECTION}' contains ${COUNT} documents"
else
    warn "Could not resolve index name — check ${BACKEND_URL}/collections"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BOLD}${GREEN}  ✓ Single ingestion test complete${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "  ${BOLD}If chunks look correct:${NC}"
echo -e "    → Delete the test collection:  curl -X DELETE ${BACKEND_URL}/collections/${MTM}"
echo -e "    → Run bulk ingestion via the Carbon UI, or POST to /ingest for each MTM"
echo ""
echo -e "  ${BOLD}If chunks look wrong:${NC}"
echo -e "    → Check CHUNKING_FIX_DETAILED.md in this directory (../) "
echo -e "    → Edit ../rag-backend/sales_manual_chunker.py"
echo -e "    → Rebuild the backend:  ./manage.sh rebuild rag-backend"
echo -e "    → Re-run this script"
echo ""

# Made with Bob
