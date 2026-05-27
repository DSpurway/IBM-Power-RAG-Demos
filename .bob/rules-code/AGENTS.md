# Code Mode - Project-Specific Rules

## Command Format Requirements

**ALWAYS provide commands in copy-paste ready format:**
- Use code blocks with proper syntax highlighting (```bash, ```python, etc.)
- Include complete commands with all necessary flags and parameters
- For multi-line commands, use proper line continuation (`\` for bash)
- Avoid inline explanations within command blocks
- Place explanations BEFORE or AFTER the code block, not inside it

Example:
```bash
# Good - Ready to copy and paste
oc start-build rag-backend --from-dir=. --follow
```

NOT:
```bash
oc start-build rag-backend --from-dir=. --follow  # This rebuilds the backend
```

## Current Deployment State

**CRITICAL**: All services are ALREADY DEPLOYED. Use rebuild commands, NOT new deployments:
```bash
oc start-build service-name --from-dir=. --follow
oc rollout status deployment/service-name
```

## IBM Power-Specific Build Requirements

### Backend Python Dependencies
MUST use IBM Power wheel repository (NOT standard PyPI for ML packages):
```dockerfile
pip install --extra-index-url=https://wheels.developerfirst.ibm.com/ppc64le/linux \
    torch==2.9.1 torchvision==0.24.1 sentence-transformers transformers
```

### OpenSearch Container
MUST use IBM-maintained ppc64le image:
```yaml
image: icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0
```

## Service Communication Patterns

### Internal Service Names (NOT External Routes)
- Backend → OpenSearch: `opensearch-service:9200`
- Backend → LLM: `granite-service:8080` or `tinyllama-service:8080`
- Frontend → Backend: `rag-backend:8080` (internal, NOT external route)

### CORS Configuration
Backend needs external route URL ONLY for browser CORS:
```python
CORS_ORIGIN = os.environ.get('CORS_ORIGIN', '*')
```

## Non-Standard Code Patterns

### Gunicorn Configuration (Backend)
```python
# MUST use these non-default settings:
--workers 1           # Single worker (avoid caching issues)
--timeout 1800        # 30 minutes (NOT default 30s) for PDF processing
```

### Docling Integration
Controlled by environment variable (NOT always enabled):
```python
USE_DOCLING = os.getenv("USE_DOCLING", "false").lower() == "true"
DOCLING_CHUNK_SIZE = 1024  # NOT default 512 - for table handling
```

### Dual LLM Model Switching
```bash
# Switch between models via environment variable
oc set env deployment/llama-service LLM_MODEL=tinyllama  # Part 1 demos
oc set env deployment/llama-service LLM_MODEL=granite    # Part 3 RAG
```

## File Structure Gotchas

- Frontend is in `Part3-RAG-Sales-Manual/carbon-rag-ui/` (NOT root)
- Backend consolidated from 5 microservices into single `rag-backend/`
- Scraper runs in Code Engine (NOT in OCP cluster)
- Old Part 3 structure (RAG-List-Collections, etc.) is DEPRECATED

## Script Preference

**ALWAYS use Git Bash (.sh) scripts, NOT PowerShell (.ps1)**
- PowerShell has formatting issues with Linux commands
- Never use `&&` in PowerShell (use `;` instead)
- Git Bash scripts work consistently across environments