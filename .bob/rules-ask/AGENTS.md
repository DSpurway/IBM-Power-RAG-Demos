# Ask Mode - Project-Specific Documentation Context

## Project Structure (Non-Obvious)

### Current State
All services are ALREADY DEPLOYED and running. Documentation should focus on improvements and troubleshooting, NOT initial deployment.

### Hybrid Cloud Architecture
- **IBM Power10 OCP Cluster**: LLM services (TinyLlama, Granite), OpenSearch, Backend, Frontend
- **IBM Code Engine**: Scraper service (dependency issues prevented OCP deployment on Power)
- **DO NOT suggest removing IBM Power components** - we want to understand performance, not avoid it

### Directory Structure Gotchas
```
Part3-RAG-Sales-Manual/
├── carbon-rag-ui/          # Frontend (NOT in root - counterintuitive)
├── rag-backend/            # Consolidated backend (replaced 5 microservices)
├── granite-service/        # Separate LLM for complex queries
├── scraper-test/           # Runs in Code Engine (NOT OCP)
└── opensearch-deployment/  # Vector DB (migrated FROM Milvus)
```

**Historical Context**: Old Part 3 had 5 separate microservices (RAG-List-Collections, RAG-Drop-Collection, RAG-Loader, RAG-Get-Docs, RAG-Prompt-LLM). Now consolidated into single `rag-backend` service.

## Documentation Locations (Hidden/Misnamed)

### Key Documentation Files
- `QUICK_START.md` - Fast deployment (but services already deployed)
- `DEPLOYMENT_WALKTHROUGH.md` - Detailed walkthrough (2298 lines - use file outline)
- `OPENSEARCH_MIGRATION.md` - Migration from Milvus to OpenSearch
- `CARBON_UI_SUMMARY.md` - Frontend features and design
- `BACKEND_CONSOLIDATION_SUMMARY.md` - Microservices consolidation details
- `POWERSHELL_SYNTAX_GUIDE.md` - PowerShell vs Bash differences (important!)

### Part-Specific READMEs
- `Part1-Deploy-LLM/README.md` - LLM deployment (dual model support)
- `Part3-RAG-Sales-Manual/README.md` - Legacy instructions (pre-consolidation)
- `Part3-RAG-Sales-Manual/rag-backend/README.md` - Current backend docs
- `Part3-RAG-Sales-Manual/carbon-rag-ui/README.md` - Frontend docs

## Non-Obvious Technical Details

### Service Communication
- **Internal routes**: Services use internal names (e.g., `opensearch-service`, `rag-backend:8080`)
- **External routes**: Only needed for browser CORS and user access
- **Counterintuitive**: Frontend talks to backend via internal route, NOT external URL

### IBM Power Specifics
- **Wheel repository**: `https://wheels.developerfirst.ibm.com/ppc64le/linux` (NOT standard PyPI)
- **OpenSearch image**: `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` (IBM-maintained, NOT Docker Hub)
- **Build times**: Granite service takes 5-10 minutes (downloads 2.5GB model)

### Techzone Environment
- **Environment-specific URLs**: Must include Techzone env number (e.g., p1293)
- **Base domain pattern**: `apps.${TECHZONE_ENV}.cecc.ihost.com`
- **Temporary environments**: Environments expire, hence GitHub sync requirement

## Script Preference Context

**CRITICAL**: Use Git Bash (.sh) scripts, NOT PowerShell (.ps1)
- PowerShell has formatting issues with Linux commands
- `&&` doesn't work in PowerShell (use `;` instead)
- Git Bash scripts are more reliable for this project
- See `POWERSHELL_SYNTAX_GUIDE.md` for details

## Custom Bob Modes

Project has custom modes in `.roomodes`:
- **techzone**: IBM Techzone and OCP deployment workflows
- **carbon**: IBM Carbon Design System and frontend development