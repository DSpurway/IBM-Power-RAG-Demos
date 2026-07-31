# Ollama RHEL/Power Checkpoint

## Decision

We are continuing the **RHEL on IBM Power** route on host `p1286-pvm1.p1286.cecc.ihost.com`, and we have **chosen Ollama** over `llama.cpp`.

### Reason
- Ollama worked on this host
- latest `llama.cpp` failed to compile cleanly on Power
- older `llama.cpp` path was more fragile operationally

## Files changed locally

- [`rag-backend/app.py`](rag-backend/app.py)
  - added explicit `ollama` backend support
  - added `OLLAMA_HOST` / `OLLAMA_PORT`
  - added `model_lower == 'ollama'` branch using the existing OpenAI-compatible code path

- [`podman/podman-compose.yml`](podman/podman-compose.yml)
  - replaced `vllm` service with `ollama`
  - backend now points to `ollama-service:11434`
  - host port remaps for shared host:
    - backend `8081:8080`
    - UI `3001:3000`

- [`podman/env.example`](podman/env.example)
  - now uses `OLLAMA_IMAGE`

- [`podman/README.md`](podman/README.md)
  - updated to Ollama-based flow

## Host state

Host:
- `p1286-pvm1.p1286.cecc.ihost.com`

Repo on host:
- `~/IBM-Power-RAG-Demos`

Podman:
- installed
- `podman-compose` installed at `~/.local/bin/podman-compose`

## Shared-host constraints

Existing host conflicts:
- port `3000` already used by another demo
- port `8080` already used by another process

Updated compose uses:
- UI: `3001`
- backend: `8081`
- Ollama: `11434`
- OpenSearch: `9200`

## Verified on host

- OpenSearch healthy on `127.0.0.1:9200`
- Ollama running on `127.0.0.1:11434`
- `granite4:latest` pulled into Ollama
- backend image built successfully

Observed:
- Ollama `/api/version` returns `{"version":"0.0.0"}` — treat as packaging quirk, not blocker

## Important sync note

The host initially still had stale vLLM-based files, but this was corrected. Verification on host showed the updated host files now contain:
- `ollama`
- `11434`
- `3001:3000`
- `8081:8080`
- `OLLAMA_IMAGE`
- `OLLAMA_HOST`

## Next step

Continue from an SSH session on the host and run:

```bash
cd ~/IBM-Power-RAG-Demos/Part3-RAG-Sales-Manual/podman
cp -f env.example .env
~/.local/bin/podman-compose --env-file .env build rag-backend carbon-ui
~/.local/bin/podman-compose --env-file .env up -d rag-backend carbon-ui
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl -s http://127.0.0.1:8081/health
```

If backend is healthy, next:
- verify UI on `http://p1286-pvm1.p1286.cecc.ihost.com:3001`

## After that

Proceed to:
1. ingestion
2. chunking validation
3. first real RAG query using Ollama-backed backend
