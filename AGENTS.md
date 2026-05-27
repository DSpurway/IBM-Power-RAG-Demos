# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Critical Project Context

**Current State**: All services are ALREADY DEPLOYED and running. Focus on improvements and fixes, NOT new deployments unless explicitly requested.

**Hybrid Cloud Architecture**: This project uses IBM Power10 (remote OCP cluster) for LLM services and Code Engine for scraper service. DO NOT remove IBM Power components without explicit agreement - we want to understand performance issues, not avoid them.

**Script Preference**: Use Git Bash scripts (.sh) instead of PowerShell (.ps1). PowerShell has formatting issues and Linux command incompatibilities. Never use `&&` in PowerShell - use `;` instead.

**GitHub Sync Required**: All changes must be synced to GitHub for reproducibility when Techzone environments expire and for team collaboration.

## Deployed Services (DO NOT REDEPLOY)

Currently running in OCP:
- `carbon-rag-ui` - Next.js frontend
- `rag-backend` - Consolidated Flask backend
- `opensearch-service` - Vector database
- `llama-service` - Dual model (TinyLlama + Granite)
- `granite-service` - Separate Granite instance for complex queries
- Scraper service in Code Engine (NOT in OCP)

## Rebuild vs Redeploy

**For code changes to existing services:**
```bash
# Rebuild and rollout (NOT new-app)
oc start-build service-name --from-dir=. --follow
oc rollout status deployment/service-name
```

**Check current state:**
```bash
oc get all -l app.kubernetes.io/part-of=ibm-power-rag-demos-app
oc get pods  # Check what's running
```

## Non-Obvious Build/Deploy Patterns

### IBM Power-Specific Wheel Installation
Backend Dockerfile MUST use IBM Power wheel repository for ML packages:
```dockerfile
pip install --extra-index-url=https://wheels.developerfirst.ibm.com/ppc64le/linux torch torchvision
```

### OpenSearch on Power
Uses IBM-maintained ppc64le image from ICR (NOT Docker Hub):
```yaml
image: icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0
```

## Critical Configuration Patterns

### Service Discovery (Internal vs External)
- **Backend to LLM/OpenSearch**: Use internal service names (e.g., `opensearch-service`, `granite-service`)
- **Frontend to Backend**: Use internal service name `rag-backend:8080` (NOT external route)
- **CORS**: Backend needs external route URL for CORS when accessed from browser

### Dual LLM Architecture
- **TinyLlama** (`tinyllama-service`): Part 1 demos, shows hallucinations
- **Granite** (`granite-service`): Part 3 RAG, better for complex queries
- Both run simultaneously, switched via environment variables

### Docling Configuration
Docling is OPTIONAL (controlled by `USE_DOCLING=true/false`). When enabled:
- Chunk size: 1024 tokens (NOT default 512) for table handling
- Models path: `/app/docling-models` (must exist in container)
- Fallback to PyPDF if Docling fails

## Non-Standard Directory Structure

```
Part3-RAG-Sales-Manual/
├── carbon-rag-ui/          # Next.js frontend (NOT in root)
├── rag-backend/            # Consolidated Flask backend (replaces 5 microservices)
├── granite-service/        # Separate LLM for complex queries
├── scraper-test/           # Runs in Code Engine (NOT OCP)
└── opensearch-deployment/  # Vector DB (NOT Milvus anymore)
```

**Migration Note**: Old Part 3 had 5 separate microservices (RAG-List-Collections, RAG-Drop-Collection, etc.). Now consolidated into single `rag-backend` service.

## Testing Commands

```bash
# Test backend health (internal)
oc exec deployment/rag-backend -- curl http://localhost:8080/health

# Test from Carbon UI pod
oc exec deployment/carbon-rag-ui -- curl http://rag-backend:8080/health

# Check which LLM model is active
oc logs deployment/llama-service | grep "Starting with"

# Monitor long-running ingestion
oc logs -f deployment/rag-backend | grep "Processing"
```

## Known Gotchas

1. **Gunicorn timeout**: Backend uses 1800s timeout for large PDF processing (NOT default 30s)
2. **Single worker**: Backend uses 1 worker to avoid caching issues across workers
3. **Techzone URLs**: Setup script (`setup-part3.sh`) requires Techzone env number (e.g., p1293)
4. **Build time**: Granite service takes 5-10 minutes (downloads 2.5GB model)
5. **Scraper location**: Scraper runs in Code Engine, NOT in OCP cluster (dependency issues on Power)

## Environment-Specific Variables

Must be set per Techzone environment:
- `TECHZONE_ENV`: Environment number (e.g., p1293)
- `BASE_DOMAIN`: Constructed as `apps.${TECHZONE_ENV}.cecc.ihost.com`
- `CORS_ORIGIN`: Either specific webpage URL or `*` for demo

## Custom Modes

Project has custom Bob modes in `.roomodes`:
- **techzone**: IBM Techzone and OCP deployment workflows
- **carbon**: IBM Carbon Design System and frontend development