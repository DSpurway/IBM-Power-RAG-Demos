#!/bin/bash
set -e

SCRAPER="https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud"
# Optional settings come from the environment or an env file, never from this script:
#   LLM_BASE_URL  OpenAI-compatible LLM used to read the question (empty = exact match only)
#   WATSON_ASSISTANT_API_KEY / _URL / _ID  legacy, leave empty to disable
[ -f "$(dirname "$0")/.env" ] && . "$(dirname "$0")/.env"

echo "Stopping and removing old rag-backend..."
podman stop rag-backend 2>/dev/null || true
podman rm rag-backend 2>/dev/null || true

echo "Starting rag-backend with SCRAPER_URL set..."
podman run -d \
  --name rag-backend \
  --network podman_rag-net \
  -p 8081:8080 \
  -e MODEL_NAME=granite4:latest \
  -e OLLAMA_HOST=ollama-service \
  -e OLLAMA_PORT=11434 \
  -e OLLAMA_MODEL=granite4:latest \
  -e OPENSEARCH_HOST=opensearch-service \
  -e OPENSEARCH_PORT=9200 \
  -e OPENSEARCH_USERNAME=admin \
  -e OPENSEARCH_PASSWORD=admin \
  -e OPENSEARCH_DB_PREFIX=rag \
  -e OPENSEARCH_INDEX_NAME=default \
  -e OPENSEARCH_NUM_SHARDS=1 \
  -e CORS_ORIGIN='*' \
  -e "SCRAPER_URL=${SCRAPER}" \
  -e "LLM_BASE_URL=${LLM_BASE_URL:-}" \
  -e "WATSON_ASSISTANT_API_KEY=${WATSON_ASSISTANT_API_KEY:-}" \
  -e "WATSON_ASSISTANT_URL=${WATSON_ASSISTANT_URL:-}" \
  -e "WATSON_ASSISTANT_ID=${WATSON_ASSISTANT_ID:-}" \
  --health-cmd='curl -sf http://localhost:8080/health || exit 1' \
  --health-interval=30s \
  --health-retries=3 \
  localhost/rag-backend:latest \
  gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 8 --timeout 1800 \
           --access-logfile - --error-logfile - app:app

echo "Waiting 10s for startup..."
sleep 10

echo "Health check:"
curl -s http://localhost:8081/health

echo ""
echo "SCRAPER_URL in container:"
podman exec rag-backend sh -c 'echo "$SCRAPER_URL"'
