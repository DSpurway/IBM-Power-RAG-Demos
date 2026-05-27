# Plan Mode - Project-Specific Architecture Context

## Current Deployment State

**CRITICAL**: All services are ALREADY DEPLOYED and running. Plans should focus on improvements, optimizations, and fixes - NOT initial deployment.

## Hybrid Cloud Architecture (Non-Standard)

### Deployed Services
```
IBM Power10 OCP Cluster:
├── carbon-rag-ui (Next.js frontend)
├── rag-backend (Flask - consolidated from 5 microservices)
├── opensearch-service (Vector DB - migrated from Milvus)
├── llama-service (Dual model: TinyLlama + Granite)
└── granite-service (Separate instance for complex queries)

IBM Code Engine:
└── scraper-service (Chromium-based - dependency issues on Power)
```

### Architectural Constraints

**DO NOT suggest removing IBM Power components** without explicit agreement:
- Purpose is to understand performance issues, not avoid them
- Power10 MMA acceleration is a key demo feature
- Techzone environments are temporary but reproducible

**Scraper Service Isolation**:
- Runs in Code Engine (NOT OCP) due to Chromium dependencies on ppc64le
- This is intentional hybrid cloud architecture
- Do not suggest moving to OCP without addressing dependency issues

## Hidden Coupling and Dependencies

### Service Communication (Non-Obvious)
- **Internal routes ONLY**: Services communicate via internal names (e.g., `opensearch-service:9200`)
- **External routes**: Only for browser CORS and user access
- **Counterintuitive**: Frontend → Backend uses internal route, NOT external URL

### Build Dependencies
- **IBM Power wheels**: MUST use `https://wheels.developerfirst.ibm.com/ppc64le/linux`
- **OpenSearch image**: MUST use `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0`
- **Standard PyPI will fail** for torch, torchvision on ppc64le

### Performance Bottlenecks (Discovered)
1. **Gunicorn timeout**: 1800s (NOT default 30s) for large PDF processing
2. **Single worker**: Required to avoid caching issues across workers
3. **Granite model download**: 5-10 minutes (2.5GB) on first build
4. **Techzone resource limits**: Cannot control core affinity (impacts LLM performance)

## Architectural Decisions (Undocumented)

### Backend Consolidation
- **Old architecture**: 5 separate microservices (RAG-List-Collections, RAG-Drop-Collection, RAG-Loader, RAG-Get-Docs, RAG-Prompt-LLM)
- **New architecture**: Single `rag-backend` service
- **Reason**: Simplified deployment, reduced resource usage, easier maintenance
- **Trade-off**: Less granular scaling (acceptable for demo)

### Dual LLM Strategy
- **TinyLlama**: Part 1 demos, intentionally shows hallucinations
- **Granite**: Part 3 RAG, better for complex queries
- **Both run simultaneously**: Switched via environment variables
- **Reason**: Demonstrate RAG value by comparing with/without context

### Docling Integration (Optional)
- **Controlled by**: `USE_DOCLING=true/false` environment variable
- **Chunk size**: 1024 tokens (NOT default 512) for table handling
- **Fallback**: PyPDF if Docling fails
- **Reason**: Better table extraction but adds complexity

## Non-Standard Patterns

### Directory Structure
```
Part3-RAG-Sales-Manual/
├── carbon-rag-ui/          # Frontend (NOT in root - counterintuitive)
├── rag-backend/            # Consolidated backend
├── granite-service/        # Separate LLM
├── scraper-test/           # Code Engine service
└── opensearch-deployment/  # Vector DB
```

**Why frontend not in root?**: Project evolved from multi-part demo structure

### Script Preference
**ALWAYS use Git Bash (.sh), NOT PowerShell (.ps1)**:
- PowerShell has formatting issues with Linux commands
- `&&` doesn't work in PowerShell (use `;` instead)
- Git Bash scripts work consistently across environments
- Critical for reproducibility when Techzone environments expire

## GitHub Sync Requirement

**All changes MUST be synced to GitHub**:
- Techzone environments are temporary (expire after reservation period)
- Team collaboration requires shared codebase
- Reproducibility when recreating demo from scratch
- Do not make local-only changes without documenting sync plan

## Environment-Specific Configuration

### Techzone Variables (Required)
- `TECHZONE_ENV`: Environment number (e.g., p1293)
- `BASE_DOMAIN`: `apps.${TECHZONE_ENV}.cecc.ihost.com`
- `CORS_ORIGIN`: Webpage URL or `*` for demo

### Setup Script Pattern
`setup-part3.sh` automates environment-specific configuration:
- Prompts for Techzone env number
- Constructs URLs dynamically
- Sets CORS for all services
- Deploys Granite service if needed

## Custom Bob Modes

Project has custom modes in `.roomodes`:
- **techzone**: IBM Techzone and OCP deployment workflows
- **carbon**: IBM Carbon Design System and frontend development