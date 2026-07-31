# Ollama RHEL/Power Checkpoint

## Current State (31 July 2026)

All four services running healthy on `p1286-pvm1.p1286.cecc.ihost.com`:

| Service | Image | Status |
|---|---|---|
| opensearch-service | icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0 | healthy |
| ollama-service | icr.io/ppc64le-oss/ollama-ppc64le:v0.17.6 | healthy |
| rag-backend | localhost/rag-backend:latest | healthy |
| carbon-rag-ui | localhost/carbon-rag-ui:latest | healthy |

Ports: UI `3001`, backend `8081`, Ollama `11434`, OpenSearch `9200`

## Model

- `granite4:latest` pulled into Ollama (3.4B, Q4_K_M, ~2.1GB)
- Ollama API: `http://ollama-service:11434/api/chat`

## Latest Commit Pending on Host

```
513f54d fix: Ollama uses /api/chat endpoint and granite4:latest model name
```

**This commit has been pushed to GitHub but NOT yet pulled/built on the host.**

### Next action on host (first thing to do):

```bash
cd ~/IBM-Power-RAG-Demos
git pull origin main
cd Part3-RAG-Sales-Manual/podman
~/.local/bin/podman-compose --env-file .env build rag-backend
podman rm -f carbon-rag-ui && podman rm -f rag-backend
~/.local/bin/podman-compose --env-file .env up -d rag-backend carbon-ui
sleep 20
curl -s http://127.0.0.1:8081/health
```

No `--no-cache` needed — only `app.py` changed so cache is fine and build will be fast.

## What Was Fixed This Session

1. **Health check** — was probing `LLAMA_HOST/health` (wrong); now probes `OLLAMA_HOST:11434/api/version`
2. **Scraper cold-start** — added `_wait_for_scraper_ready()` helper that probes `ibm-power-announcements` page to confirm Selenium is ready before real scrape
3. **SCRAPER_URL** — added to `podman-compose.yml` (was defaulting to `host.docker.internal:5000` which doesn't work in Podman)
4. **OLLAMA_MODEL** — added to `podman-compose.yml` as `granite4:latest`
5. **Ollama API format** — was using `openai` format (`/v1/chat/completions`, model `granite`); now uses `ollama` format (`/api/chat`, model from `OLLAMA_MODEL` env var)
6. **Ollama response parsing** — added `llm_format == 'ollama'` branch that reads `result['message']['content']`
7. **git on host** — set `pull.rebase true` globally, set identity to `DSpurway / david.spurway@uk.ibm.com`

## Data State

- **One collection ingested**: `9080-M9S` (IBM Power System E980)
- **1301 chunks**, **990 sections** scraped
- Index: `rag_d0f9e9bb718684771b4eb639bf167a2d`
- OpenSearch is on a named volume (`opensearch-data`) — data persists across container restarts

## Immediate Next Steps (after build above)

### 1. Test first RAG query
```bash
curl -s -X POST http://127.0.0.1:8081/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is feature code 0010 on the IBM Power E980 9080-M9S?",
    "model": "ollama",
    "server_mtm": "9080-M9S"
  }' | python3 -m json.tool
```

Expected: answer should include withdrawal date `January 12, 2024`, CSU, min/max attributes.

### 2. Validate chunking quality
Key things to check:
- Feature code `(#0010)` chunk is retrieved (not just chunks that mention `0010` in passing)
- Withdrawal date is present in the retrieved chunk
- Structured attributes (CSU, min/max, OS level) are in the chunk

### 3. Chunking fixes still outstanding (in `sales_manual_chunker.py`)

These are queued but not yet made:

**Fix 1: `_find_section` boundary detection** — current regex `\n^[A-Z][a-z\s]+$\n` matches ANY short Title Case line and cuts sections off early. Replace with a fixed list of known major section names:

```python
MAJOR_SECTIONS = [
    'Abstract', 'Highlights', 'Description', 'Models',
    'Technical description', 'Publications', 'Features',
    'Accessories', 'Supplies', 'Trademarks', 'Specifications',
    'Product life cycle dates', 'Product positioning'
]
```

**Fix 2: `_clean_section_text`** — strips feature code heading lines (`(#XXXX) Name`) from general sections, orphaning body text without its context heading. Remove that stripping logic entirely.

**Fix 3: `Technical description` splitting** — uses character-count `RecursiveCharacterTextSplitter` which cuts mid-sentence. Should prefer `\n\n` paragraph boundaries first.

### 4. After chunking fixes
- Re-ingest E980 to validate improved chunk quality
- If good, proceed to bulk ingestion of all servers

## Scraper

- URL: `https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud`
- Selenium-based (Code Engine), scales to zero when idle
- Warm-up probe page: `https://www.ibm.com/support/pages/ibm-power-announcements`
- Cold start: container up in ~30s, Selenium ready ~10-30s after that
- Previous cold-start failure mode: returned `success: False` with `"Could not find ibmdocs-content-container"` — this was a transient Selenium init issue, not a permanent selector problem

## SSH Access

```bash
ssh -i C:\Users\029878866\Downloads\rag_key.pem -o StrictHostKeyChecking=no cecuser@p1286-pvm1.p1286.cecc.ihost.com
# Key copied to: C:\Users\029878866\Downloads\rag_key.pem
```

## Git State

- Remote: `https://github.com/DSpurway/IBM-Power-RAG-Demos.git` (origin)
- Host is now on `git reset --hard origin/main` — clean, no local commits
- `pull.rebase true` set globally on host
- Identity set: `DSpurway / david.spurway@uk.ibm.com`
- **Rule**: always `git pull origin main` before editing on host

## Known Issues / Notes

- Port scan noise in backend logs from `10.89.0.4` (Nessus/Tenable IBM compliance scan) — filter with `grep -v "cgi-bin\|jndi\|nessus"`
- `podman rm -f` order matters: always remove `carbon-rag-ui` before `rag-backend` (dependency)
- `podman system prune -f` recovered 16GB when disk hit 90% — run if space gets tight again
- `WARN: HEALTHCHECK not supported for OCI image format` — harmless, Podman quirk
