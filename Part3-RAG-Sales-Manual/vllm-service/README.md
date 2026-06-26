# vLLM Service — IBM Power (ppc64le)

Replaces the llama.cpp Granite service with the pre-built vLLM CPU inference engine
from the IBM project-ai-services component library.

## Image

```
icr.io/ppc64le-oss/vllm-ppc64le:0.19.1
```

Pulled from IBM Container Registry (`ppc64le-oss` namespace — **no authentication required**).  
Source: [project-ai-services/ai-services/assets/components/llm/vllm-cpu](https://github.com/IBM/project-ai-services/tree/main/ai-services/assets/components/llm/vllm-cpu)

## API

vLLM exposes an **OpenAI-compatible** REST API on port **8000**:

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `POST /v1/chat/completions` | Chat completions (used by rag-backend) |
| `POST /v1/completions` | Legacy completions |
| `GET /v1/models` | List loaded models |

## Deploy to OCP

```bash
cd Part3-RAG-Sales-Manual/vllm-service
oc apply -f vllm-svc.yaml
oc apply -f vllm-deploy.yaml
oc apply -f vllm-route.yaml
oc rollout status deployment/vllm-service --timeout=20m
```

## How the model is loaded

vLLM loads models from `/models/<model-name>` inside the container.  
The deployment uses an `emptyDir` volume and relies on `HF_HUB_OFFLINE=0` so vLLM
downloads the model from Hugging Face on first start into the volume.

The model is: **ibm-granite/granite-4.0-tiny-instruct** (HuggingFace safetensors format,
~1–2 GB — much smaller than the 4GB GGUF used by llama.cpp).

> **First-start time**: ~5–10 minutes (model download). Subsequent starts: immediate (volume persists while pod is running).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VLLM_CPU_OMP_THREADS_BIND` | `auto` | Bind OpenMP threads to CPUs automatically |
| `VLLM_CPU_KVCACHE_SPACE` | `8` | KV cache size in GB (increase if memory allows) |
| `HF_HUB_OFFLINE` | `0` | Set to `1` to disable HuggingFace downloads |

## Backend Integration

The `rag-backend` service detects vLLM via the `LLM_API_FORMAT` environment variable:

```bash
# Use vLLM (OpenAI-compatible)
oc set env deployment/rag-backend LLM_API_FORMAT=openai GRANITE_HOST=vllm-service GRANITE_PORT=8000

# Revert to llama.cpp
oc set env deployment/rag-backend LLM_API_FORMAT=llamacpp GRANITE_HOST=granite-service GRANITE_PORT=8080
```

## Performance (reference from project-ai-services team)

Tested on IBM Power with full Granite model:
- **Generation throughput**: ~7.2–7.3 tokens/s
- **Prompt throughput**: ~2.5 tokens/s (initial)

With Granite 4.0 Tiny (smaller model), throughput should be higher.

## Resource Requirements

| Resource | Request | Limit |
|---|---|---|
| Memory | 16Gi | 24Gi |
| CPU | 4 cores | 8 cores |

Significantly less than the 150Gi used by the ai-services team (they run much larger models).

# Made with Bob
