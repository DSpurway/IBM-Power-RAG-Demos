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
│  │ ollama-service  │ :11434  (IBM ppc64le Ollama image) │
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
| Ollama (Granite) | 11434 | `icr.io/ppc64le-oss/ollama-ppc64le:v0.17.6` |
| OpenSearch | 9200 | `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` |

### Why Ollama instead of llama.cpp?

The IBM Container Registry provides a `ppc64le` Ollama image that starts cleanly on this RHEL Power environment and exposes an OpenAI-compatible API (`/v1/chat/completions`). The RAG backend can therefore use Ollama with only environment/config changes, pointing `GRANITE_HOST` / `GRANITE_PORT` at `ollama-service:11434`.

---

## Quick Start

### 1. Reserve a TechZone environment

- **Collection**: [Generative AI demos on IBM Power](https://techzone.ibm.com/collection/generative-ai-demos-on-ibm-power)
- **Image**: RHEL 9 ready for AI on IBM Power10 (IaaS)
- Wait ~15–30 min for provisioning

### 2. SSH into the LPAR and clone the repo

```bash
ssh cecuser@<your-lpar-fqdn>

git clone https://github.com/DSpurway/IBM-Power-RAG-Demos.git
cd IBM-Power-RAG-Demos/Part3-RAG-Sales-Manual/podman
```

### 3. (Optional) Configure environment

```bash
cp env.example .env
# Edit .env if you want a different Ollama image tag or Watson credentials
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

> **First run note**: start Ollama, then pull the Granite model inside the container before testing queries.
> Example: `podman exec ollama-service ollama pull granite4:latest`
> Check progress with `./manage.sh logs ollama`.

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
./manage.sh logs ollama         # tail Ollama logs
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

### Ollama model is not ready yet
Expected before the first model pull completes.
```bash
./manage.sh logs ollama
podman exec ollama-service ollama list
podman exec ollama-service ollama pull granite4:latest
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
