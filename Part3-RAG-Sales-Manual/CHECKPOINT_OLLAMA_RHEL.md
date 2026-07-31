# Ollama RHEL/Power Checkpoint

## Current State (31 July 2026 — end of session 2)

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

## Latest Commit on Host

```
5319942 feat: feature code direct lookup with tight LLM prompt + raw_chunk in response
```

**This commit has been pushed to GitHub but NOT yet pulled/built on the host.**

### Next action on host (first thing to do next session):

```bash
cd ~/IBM-Power-RAG-Demos
git pull origin main
cd Part3-RAG-Sales-Manual/podman
~/.local/bin/podman-compose --env-file .env build rag-backend
podman rm -f carbon-rag-ui && podman rm -f rag-backend
~/.local/bin/podman-compose --env-file .env up -d rag-backend carbon-ui
sleep 25
curl -s http://127.0.0.1:8081/health | python3 -m json.tool
```

Then re-ingest E980 (sections fix needs a fresh ingest):

```bash
curl -s -X DELETE http://127.0.0.1:8081/api/collections/rag_mtm_9080_m9s | python3 -m json.tool
curl -s --max-time 300 -X POST http://127.0.0.1:8081/api/ingest-sales-manual \
  -H "Content-Type: application/json" \
  -d '{
    "mtm": "9080-M9S",
    "server_model": "E980",
    "server_name": "IBM Power System E980",
    "processor": "POWER9",
    "url": "https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s"
  }' | python3 -m json.tool
```

Then test feature code direct lookup:

```bash
curl -s -X POST http://127.0.0.1:8081/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is feature code #EFP1 on the IBM Power E980?",
    "model": "ollama",
    "server_mtm": "9080-M9S"
  }' | python3 -m json.tool
```

Expected:
- `processing_method: "feature_code_direct_lookup"`
- `raw_chunk` contains the full `(#EFP1)` section text
- `content` is LLM answer constrained to that chunk
- `chunks_used[0].metadata.is_withdrawn: true`
- `chunks_used[0].metadata.withdrawal_date: "January 12, 2024"`
- `chunks_used[0].metadata.chunk_strategy: "structured_section"` ← confirms sections fix worked

## Watson Assistant

Credentials are in `.env` on the host (NOT in git). Set via:

```bash
cd ~/IBM-Power-RAG-Demos/Part3-RAG-Sales-Manual/podman
grep WATSON .env   # verify they are present
```

Values come from `rag-backend/watson-assistant-credentials.yaml` (shared demo instance).
Watson is confirmed working — session created, `Check_Date` intent detected at 0.982 confidence.

## What Was Fixed This Session

1. **Chunker v1.1.0** (`sales_manual_chunker.py`) — three fixes:
   - `_find_section()`: replace generic Title Case regex boundary with `MAJOR_SECTIONS` fixed list
   - `_clean_section_text()`: stop stripping `(#XXXX)` heading lines (was orphaning body text)
   - Version bumped `1.0.0 → 1.1.0`

2. **Sections passed to chunker** (`app.py`) — `transformed_data` was dropping the `sections` array from the Code Engine scraper response; chunker was always falling back to plain-text regex, finding inline `(#EFP1)` references instead of proper subheadings. One-line fix: forward `sections` too.

3. **`import re` at module level** (`app.py`) — was only imported inside `generate()` function body. Adding `re.sub()` calls for search prompt stripping caused `UnboundLocalError` (Python treats any name assigned anywhere in a function as local throughout). Fixed by adding `import re` at module level and removing the two inner imports.

4. **Search prompt stripping** (`app.py`) — strip known `server_model` / `server_mtm` / "IBM Power" tokens from the search query before embedding/BM25. These tokens are identical across every chunk in the collection and dilute the actual topic signal.

5. **Feature code direct lookup** (`app.py`) — "what is feature code #EFP1" queries now bypass semantic search entirely. Term query on `metadata.feature_code`. Tight LLM prompt constrained to single chunk. Returns both `content` (LLM answer) and `raw_chunk` (for human verification).

6. **Richer `chunks_used` metadata** (`app.py`) — now surfaces `chunk_strategy`, `chunker_version`, `feature_code`, `feature_name`, `is_withdrawn`, `withdrawal_date` in every response.

7. **Watson Assistant credentials** — added to `.env` on host. Watson confirmed connecting and classifying at high confidence.

## Data State

- **One collection ingested**: `9080-M9S` (IBM Power System E980)
- **1021 chunks** (down from 1301 — structured sections path now active, fewer duplicates)
- **990 sections** scraped
- Index: `rag_mtm_9080_m9s` (note: collection name changed from `rag_d0f9e9bb...`)
- `chunker_version: "1.1.0"` on all chunks
- OpenSearch on named volume (`opensearch-data`) — persists across restarts

**Note**: Current ingested data used the sections fix but NOT the latest build (5319942).
A fresh re-ingest is needed next session to pick up all fixes together.

## Immediate Next Steps (start of next session)

1. Pull, rebuild, re-ingest (commands above)
2. Validate `chunk_strategy: "structured_section"` on feature code chunks
3. Test feature code direct lookup end-to-end
4. If chunking looks good — consider bulk ingestion of all servers

## Query Routing Summary (current state)

| Query type | Example | Path | LLM? |
|---|---|---|---|
| Lifecycle date | "When was E980 withdrawn?" | Watson → table_lookup → OpenSearch term | ❌ No |
| Feature code lookup | "What is #EFP1?" | Watson → feature_code_direct_lookup → OpenSearch term | ✅ Tight prompt |
| General RAG | "What memory options are available?" | Watson → RAG → hybrid search → reranker | ✅ Full RAG |

## SSH Access

```bash
ssh -i C:\Users\029878866\Downloads\rag_key.pem -o StrictHostKeyChecking=no cecuser@p1286-pvm1.p1286.cecc.ihost.com
```

## Git State

- Remote: `https://github.com/DSpurway/IBM-Power-RAG-Demos.git`
- Latest commit: `5319942`
- Host is behind — needs `git pull origin main` at start of next session
- `pull.rebase true` set globally on host

## Known Issues / Notes

- Port scan noise in backend logs from `10.89.0.4` — filter with `grep -v "cgi-bin\|jndi\|nessus"`
- `podman rm -f` order matters: always remove `carbon-rag-ui` before `rag-backend`
- `WARN: HEALTHCHECK not supported for OCI image format` — harmless Podman quirk
- Watson Assistant adds ~500ms latency per query (eu-gb API round-trip) — expected
- Feature code `metadata.feature_code` field uses keyword mapping in OpenSearch — term query works correctly without analysing
