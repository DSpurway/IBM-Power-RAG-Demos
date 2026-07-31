#!/bin/bash
# =============================================================================
# deploy.sh — Bootstrap RAG Demo on a fresh RHEL IBM Power LPAR
# =============================================================================
# Run this ONCE on the RHEL LPAR after cloning the repo.
# It installs Podman, podman-compose, builds the two custom images,
# and starts all services.
#
# Usage (on the RHEL LPAR):
#   git clone https://github.com/DSpurway/IBM-Power-RAG-Demos.git
#   cd IBM-Power-RAG-Demos/Part3-RAG-Sales-Manual/podman
#   cp env.example .env          # edit .env if needed (Watson creds, model choice)
#   chmod +x deploy.sh manage.sh ingest-single.sh
#   ./deploy.sh
# =============================================================================

set -euo pipefail

# ── Colours (same palette as Carbon-GenAI-Demos) ─────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Two levels up from Part3-RAG-Sales-Manual/podman/ to reach the repo root
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${HOME}/rag-deploy-logs"
LOG_FILE="${LOG_DIR}/deploy-$(date +%Y%m%d-%H%M%S).log"
START_TIME=$(date +%s)
TOTAL_STEPS=7
CURRENT_STEP=0

mkdir -p "${LOG_DIR}"

# ── Logging helpers ───────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*" >> "${LOG_FILE}"; }
step() { CURRENT_STEP=$((CURRENT_STEP+1))
         echo -e "\n${BOLD}${CYAN}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} $*"
         log "STEP [${CURRENT_STEP}/${TOTAL_STEPS}] $*"; }
ok()   { echo -e "  ${GREEN}✓${NC} $*"; log "OK   $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; log "WARN $*"; }
err()  { echo -e "  ${RED}✗${NC}  $*"; log "ERR  $*"; }
info() { echo -e "  ${BLUE}ℹ${NC}  $*"; log "INFO $*"; }

elapsed() {
    local s=$(( $(date +%s) - START_TIME ))
    printf "%dm %ds" $((s/60)) $((s%60))
}

# ── Banner ────────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BOLD}${CYAN}  IBM Power RAG Demo — Podman/RHEL Deployment${NC}"
echo -e "${BLUE}  https://github.com/EMEA-AI-SQUAD/RAG-with-Notebook${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Log file: ${LOG_FILE}"
echo ""

# ── Pre-flight ────────────────────────────────────────────────────────────────
step "Pre-flight checks"

if [[ "$(uname -m)" != "ppc64le" ]]; then
    warn "Architecture is $(uname -m) — expected ppc64le. Some images may not work."
fi

if [[ ! -f /etc/redhat-release ]]; then
    warn "This script targets RHEL. Proceeding anyway but results may vary."
fi

# Check for .env
if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
    warn ".env not found — copying env.example to .env"
    cp "${SCRIPT_DIR}/env.example" "${SCRIPT_DIR}/.env"
    info "Edit ${SCRIPT_DIR}/.env to customise the vLLM model or add Watson credentials."
fi

# Disk space check (need at least 20 GB for model + images)
FREE_GB=$(df -BG "${HOME}" | awk 'NR==2 {gsub("G",""); print $4}')
if [[ "${FREE_GB}" -lt 20 ]]; then
    warn "Only ${FREE_GB}GB free. Model download needs ~20 GB. Consider freeing space."
else
    ok "Disk space: ${FREE_GB}GB available"
fi

ok "Pre-flight complete"

# ── Install system packages ───────────────────────────────────────────────────
step "Installing Podman and podman-compose"

if command -v podman &>/dev/null; then
    ok "Podman already installed: $(podman --version)"
else
    info "Installing podman…"
    sudo dnf install -y podman >> "${LOG_FILE}" 2>&1
    ok "Podman installed: $(podman --version)"
fi

if command -v podman-compose &>/dev/null; then
    ok "podman-compose already installed: $(podman-compose --version)"
else
    info "Installing podman-compose…"
    # podman-compose is in EPEL; try dnf first then pip
    if sudo dnf install -y podman-compose >> "${LOG_FILE}" 2>&1; then
        ok "podman-compose installed via dnf"
    else
        warn "dnf install failed — trying pip3"
        pip3 install --user podman-compose >> "${LOG_FILE}" 2>&1
        ok "podman-compose installed via pip3"
    fi
fi

# ── Configure Podman for rootless operation ───────────────────────────────────
step "Configuring rootless Podman"

# Enable lingering so user containers survive logout
if loginctl enable-linger "$(whoami)" >> "${LOG_FILE}" 2>&1; then
    ok "Linger enabled for $(whoami)"
else
    warn "Could not enable linger — containers will stop on logout"
fi

# Increase inotify limits (OpenSearch needs this)
if grep -q "fs.inotify.max_user_watches" /etc/sysctl.conf 2>/dev/null; then
    ok "inotify limits already set"
else
    echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf >> "${LOG_FILE}" 2>&1
    sudo sysctl -p >> "${LOG_FILE}" 2>&1
    ok "inotify limits increased"
fi

# vm.max_map_count — required by OpenSearch
if sudo sysctl -w vm.max_map_count=262144 >> "${LOG_FILE}" 2>&1; then
    if ! grep -q "vm.max_map_count" /etc/sysctl.conf; then
        echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf >> "${LOG_FILE}"
    fi
    ok "vm.max_map_count=262144 set (required by OpenSearch)"
else
    warn "Could not set vm.max_map_count — OpenSearch may fail to start"
fi

# ── Build custom images ───────────────────────────────────────────────────────
step "Building RAG backend image"

info "Building rag-backend (this can take 5–10 min on first run)…"
podman build \
    --tag localhost/rag-backend:latest \
    "${REPO_ROOT}/Part3-RAG-Sales-Manual/rag-backend" \
    2>&1 | tee -a "${LOG_FILE}"
ok "rag-backend image built"

step "Building Carbon UI image"

info "Building carbon-rag-ui (this takes ~3 min)…"
podman build \
    --tag localhost/carbon-rag-ui:latest \
    "${REPO_ROOT}/Part3-RAG-Sales-Manual/carbon-rag-ui" \
    2>&1 | tee -a "${LOG_FILE}"
ok "carbon-rag-ui image built"

# ── Start services ────────────────────────────────────────────────────────────
step "Starting all services with podman-compose"

cd "${SCRIPT_DIR}"
podman-compose --env-file .env up -d 2>&1 | tee -a "${LOG_FILE}"

# Wait for OpenSearch to become healthy before finishing
info "Waiting for OpenSearch to be ready (up to 2 min)…"
for i in $(seq 1 24); do
    if curl -sf http://localhost:9200/_cluster/health &>/dev/null; then
        ok "OpenSearch is healthy"
        break
    fi
    if [[ $i -eq 24 ]]; then
        warn "OpenSearch not yet healthy after 2 min — check: podman logs opensearch-service"
    fi
    sleep 5
done

info "Waiting for RAG backend to be ready (up to 1 min)…"
for i in $(seq 1 12); do
    if curl -sf http://localhost:8080/health &>/dev/null; then
        ok "RAG backend is healthy"
        break
    fi
    if [[ $i -eq 12 ]]; then
        warn "RAG backend not yet healthy — check: podman logs rag-backend"
    fi
    sleep 5
done

# ── Summary ───────────────────────────────────────────────────────────────────
FQDN=$(hostname -f 2>/dev/null || hostname)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BOLD}${GREEN}  ✓ Deployment complete  ($(elapsed))${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "  ${BOLD}Carbon RAG UI:${NC}    http://${FQDN}:3000"
echo -e "  ${BOLD}RAG Backend:${NC}      http://${FQDN}:8080"
echo -e "  ${BOLD}vLLM API:${NC}         http://${FQDN}:8000"
echo -e "  ${BOLD}OpenSearch:${NC}       http://${FQDN}:9200"
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo -e "    Test single ingestion:  ./ingest-single.sh <mtm> <url>"
echo -e "    Check service status:   ./manage.sh status"
echo -e "    Tail logs:              ./manage.sh logs <service>"
echo -e "    Stop all:               ./manage.sh stop"
echo ""
echo -e "  ${BOLD}Log file:${NC} ${LOG_FILE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Made with Bob
