# Podman / RHEL Deployment

Run the IBM Power Sales Manual RAG demo on a **RHEL LPAR on IBM Power (ppc64le)** using **Podman** — an alternative to the OpenShift manifests in the parent directory.

This folder lives alongside the existing OCP manifests and Dockerfiles in `Part3-RAG-Sales-Manual/` and reuses them directly — no code is duplicated.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  RHEL 9 LPAR  (IBM Power ppc64le)                        │
│                                                           │
│  ┌─────────────────┐   rag-net (Podman bridge)           │
│  │  carbon-rag-ui  │ :3000 ──→ rag-backend:8080          │
│  └─────────────────┘                                     │
│                                                           │
│  ┌─────────────────┐   OpenAI-compatible API             │
│  │  vllm-service   │ :8000   (IBM project-ai-services    │
│  │  (ppc64le CPU)  │          vllm-cpu image)            │
│  └─────────────────┘                                     │
│                                                           │
│  ┌─────────────────┐   vector store                      │
│  │   opensearch    │ :9200   (icr.io/ppc64le-oss)        │
│  └─────────────────┘                                     │
└──────────────────────────────────────────────────────────┘
```

| Service | Port | Image |
|---|---|---|
| Carbon RAG UI | 3000 | Built locally from `../carbon-rag-ui` |
| RAG Backend | 8080 | Built locally from `../rag-backend` |
| vLLM (Granite) | 8000 | `ghcr.io/ibm/project-ai-services/vllm-cpu:latest` |
| OpenSearch | 9200 | `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` |

### Why vLLM instead of llama.cpp?

The IBM [project-ai-services](https://github.com/IBM/project-ai-services) team maintains a `vllm-cpu` container image optimised for ppc64le.  It exposes the same OpenAI-compatible API (`/v1/chat/completions`) as llama.cpp's server, so the RAG backend works without code changes — only the `GRANITE_HOST` / `GRANITE_PORT` env vars are updated to point at `vllm-service:8000`.

---

## Quick Start

### 1. Reserve a TechZone environment

- **Collection**: [Generative AI demos on IBM Power](https://techzone.ibm.com/collection/generative-ai-demos-on-ibm-power)
- **Image**: RHEL 9 ready for AI on IBM Power10 (IaaS)
- Wait ~15–30 min for provisioning

### 2. SSH into the LPAR and clone the repo

```bash
ssh cecuser@<your-lpar-fqdn>

git clone https://github.com/EMEA-AI-SQUAD/RAG-with-Notebook.git
cd RAG-with-Notebook/Part3-RAG-Sales-Manual/podman
```

### 3. (Optional) Configure environment

```bash
cp env.example .env
# Edit .env if you want a different Granite model or Watson credentials
nano .env
```

### 4. Deploy

```bash
chmod +x deploy.sh manage.sh ingest-single.sh
./deploy.sh
```

The deploy script will:
1. Install Podman and podman-compose
2. Set kernel parameters required by OpenSearch
3. Build the RAG backend and Carbon UI images from the sibling directories
4. Start all four services
5. Wait for OpenSearch and the backend to become healthy

> **First run note**: vLLM downloads the Granite model (~4 GB) on first start.  
> The UI and backend are available immediately; vLLM queries will queue until the model is loaded.  
> Check progress with `./manage.sh logs vllm`.

### 5. Access the demo

Open your browser at: `http://<your-lpar-fqdn>:3000`

---

## Validating Chunking (Before Bulk Ingestion)

Before ingesting all Sales Manuals, test one to verify the chunker is producing good output:

```bash
./ingest-single.sh "9009-42A" \
  "https://www.ibm.com/docs/en/power9?topic=9009-42a-sales-manual"
```

The script shows:
- Total chunks created
- Breakdown by chunk type (`lifecycle_table`, `feature_code`, `content_section`)
- A text preview of the first chunk of each type
- The document count in OpenSearch

If chunks look wrong, edit [`../rag-backend/sales_manual_chunker.py`](../rag-backend/sales_manual_chunker.py) then rebuild and retest:

```bash
./manage.sh rebuild rag-backend
./ingest-single.sh "9009-42A" "<url>"
```

See [`../CHUNKING_FIX_DETAILED.md`](../CHUNKING_FIX_DETAILED.md) for a full description of known chunking issues and fixes.

Once a single ingestion looks correct, use the Carbon UI to trigger bulk ingestion.

---

## Day-to-Day Management

```bash
./manage.sh status              # health of all services
./manage.sh logs vllm           # tail vLLM logs (useful during model load)
./manage.sh logs rag-backend    # tail RAG backend logs
./manage.sh restart rag-backend # restart one service (after a code change)
./manage.sh rebuild rag-backend # rebuild image + restart (after code change)
./manage.sh rebuild carbon-ui   # rebuild UI image + restart
./manage.sh stop                # stop the whole stack
./manage.sh start               # start the whole stack
```

---

## Files in This Directory

| File | Purpose |
|---|---|
| `podman-compose.yml` | Defines all four services, networks, and volumes |
| `env.example` | Template for `.env` — copy and edit, never commit |
| `deploy.sh` | One-shot bootstrap script for a fresh RHEL LPAR |
| `manage.sh` | Start / stop / status / logs / rebuild |
| `ingest-single.sh` | Test chunking for one Sales Manual URL before bulk |

---

## Troubleshooting

### OpenSearch fails to start
```bash
# Check kernel parameter
sysctl vm.max_map_count   # should be 262144
sudo sysctl -w vm.max_map_count=262144

./manage.sh restart opensearch
./manage.sh logs opensearch
```

### vLLM is slow to respond
Expected on first start — the model download takes several minutes.
```bash
./manage.sh logs vllm
# Watch for "Application startup complete"
```

### RAG backend cannot reach OpenSearch
```bash
# Test from inside the backend container
podman exec rag-backend curl -s http://opensearch-service:9200/_cluster/health
```

### Port already in use
```bash
ss -tlnp | grep 8080
./manage.sh stop && ./manage.sh start
```

---

*Made with Bob — IBM EMEA AI Squad*
