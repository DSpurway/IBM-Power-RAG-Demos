#!/bin/bash
# =============================================================================
# deploy-lpar.sh - run the IBM Power Sales Manual Assistant on the shared Spyre LPAR
# =============================================================================
# Run ON the LPAR as the unprivileged user (david), rootless podman only.
# Touches nothing outside this stack: it only creates/replaces the three containers,
# the network and the two volumes named below (all prefixed "sa-" / "sales-assistant").
#
# Expected layout (staged from the laptop, see ../README.md "Spyre LPAR"):
#   ~/sales-assistant/rag-backend/     source for the backend image (Dockerfile, *.py, pdfs/, sources.json)
#   ~/sales-assistant/carbon-rag-ui/   Containerfile, nginx.conf.tmpl and the built build/ directory
#   ~/sales-assistant/.env             optional overrides (LLM_BASE_URL, LLM_MODEL, ...)
#
# Usage:
#   ./deploy-lpar.sh preflight       read-only checks
#   ./deploy-lpar.sh build [be|ui]   build images (default: both)
#   ./deploy-lpar.sh up              (re)create network, volumes and containers
#   ./deploy-lpar.sh status
#   ./deploy-lpar.sh logs <opensearch|backend|ui>
#   ./deploy-lpar.sh refresh <install|remove|status|run>   daily Sales Manual change check (user systemd timer)
#   ./deploy-lpar.sh down            stop and remove the containers (volumes are kept)
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/sales-assistant}"
[[ -f "${APP_DIR}/.env" ]] && set -a && source "${APP_DIR}/.env" && set +a

NET=sales-assistant-net
C_OS=sa-opensearch
C_BE=sa-rag-backend
C_UI=sa-ui
V_OS=sa-opensearch-data
V_HF=sa-hf-cache
IMG_BE=localhost/sa-rag-backend:latest
IMG_UI=localhost/sa-ui:latest
IMG_OS=icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0

UI_PORT="${UI_PORT:-8400}"          # agreed with Andrew (84xx, IBM network only)
BE_PORT="${BE_PORT:-8401}"          # bound to localhost only
LLM_MODEL="${LLM_MODEL:-ibm-granite/granite-4.1-8b-fp8}"
SCRAPER_URL="${SCRAPER_URL:-https://ibm-docs-scraper-enhanced.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud}"   # Code Engine
SPYRE_LLM_CONTAINER="${SPYRE_LLM_CONTAINER:-llm-1241b938ce-llm}"   # Spyre "Digital Assistant"

say() { echo "[$(date '+%H:%M:%S')] $*"; }

# The Spyre LLM address is assigned by podman (root) and can change when Andrew's pods restart.
resolve_llm_base_url() {
    if [[ -n "${LLM_BASE_URL:-}" ]]; then echo "${LLM_BASE_URL}"; return; fi
    local ip
    ip=$(sudo -n podman inspect "${SPYRE_LLM_CONTAINER}" \
         --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' 2>/dev/null | awk '{print $1}')
    if [[ -n "${ip}" ]]; then echo "http://${ip}:8000"; fi
}

preflight() {
    say "Architecture: $(uname -m); podman: $(podman --version)"
    say "linger: $(loginctl show-user "$(whoami)" -p Linger 2>/dev/null || echo unknown)"
    say "vm.max_map_count: $(sysctl -n vm.max_map_count) (OpenSearch needs >= 262144)"
    for p in "${UI_PORT}" "${BE_PORT}"; do
        if ss -ltn | awk '{print $4}' | grep -q ":${p}\$"; then say "PORT ${p} IS IN USE"; else say "port ${p} free"; fi
    done
    local url; url=$(resolve_llm_base_url || true)
    say "LLM base URL: ${url:-NOT RESOLVED}"
    if [[ -n "${url}" ]]; then
        say "LLM /v1/models: HTTP $(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${url}/v1/models" || echo fail)"
    fi
    say "internet (huggingface.co, for the embedding + reranker models): HTTP $(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://huggingface.co || echo fail)"
    say "free space in \$HOME: $(df -h "${HOME}" | awk 'NR==2{print $4}')"
}

build() {
    local what="${1:-all}"
    if [[ "${what}" == "all" || "${what}" == "be" ]]; then
        say "Building ${IMG_BE} (first build is slow: torch + sentence-transformers wheels for ppc64le)"
        podman build -t "${IMG_BE}" "${APP_DIR}/rag-backend"
    fi
    if [[ "${what}" == "all" || "${what}" == "ui" ]]; then
        say "Building ${IMG_UI} (static files only)"
        podman build -t "${IMG_UI}" -f "${APP_DIR}/carbon-rag-ui/Containerfile" "${APP_DIR}/carbon-rag-ui"
    fi
}

up() {
    local llm; llm=$(resolve_llm_base_url || true)
    if [[ -z "${llm}" ]]; then say "WARNING: LLM_BASE_URL not resolved; the backend will start without an LLM"; fi

    podman network exists "${NET}" || podman network create "${NET}" >/dev/null
    podman volume exists "${V_OS}" || podman volume create "${V_OS}" >/dev/null
    podman volume exists "${V_HF}" || podman volume create "${V_HF}" >/dev/null

    for c in "${C_UI}" "${C_BE}" "${C_OS}"; do podman rm -f "${c}" >/dev/null 2>&1 || true; done

    say "Starting OpenSearch (internal only, no published port)"
    podman run -d --name "${C_OS}" --network "${NET}" --restart always \
        -e discovery.type=single-node \
        -e OPENSEARCH_JAVA_OPTS="-Xms2g -Xmx2g" \
        -e DISABLE_SECURITY_PLUGIN=true \
        -e DISABLE_INSTALL_DEMO_CONFIG=true \
        -v "${V_OS}:/usr/share/opensearch/data" \
        "${IMG_OS}" >/dev/null

    say "Waiting for OpenSearch (up to 3 min)"
    for _ in $(seq 1 36); do
        if podman exec "${C_OS}" curl -sf http://localhost:9200/_cluster/health >/dev/null 2>&1; then break; fi
        sleep 5
    done

    say "Starting rag-backend on 127.0.0.1:${BE_PORT}"
    podman run -d --name "${C_BE}" --network "${NET}" --restart always \
        -p "127.0.0.1:${BE_PORT}:8080" \
        -e OPENSEARCH_HOST="${C_OS}" -e OPENSEARCH_PORT=9200 \
        -e OPENSEARCH_USERNAME=admin -e OPENSEARCH_PASSWORD=admin -e OPENSEARCH_DB_PREFIX=rag \
        -e LLM_BASE_URL="${llm}" -e LLM_MODEL="${LLM_MODEL}" \
        -e SCRAPER_URL="${SCRAPER_URL}" \
        -e CORS_ORIGIN='*' \
        -e HF_HOME=/hf-cache \
        -v "${V_HF}:/hf-cache" \
        "${IMG_BE}" >/dev/null

    say "Starting UI on 0.0.0.0:${UI_PORT}"
    podman run -d --name "${C_UI}" --network "${NET}" --restart always \
        -p "${UI_PORT}:8400" \
        -e BACKEND_HOST="${C_BE}" -e BACKEND_PORT=8080 \
        "${IMG_UI}" >/dev/null

    # Containers with --restart always come back after a reboot via the user's podman-restart.service
    systemctl --user enable podman-restart.service >/dev/null 2>&1 || say "could not enable podman-restart.service (containers will not auto-start after a reboot)"
    status
}

status() {
    podman ps -a --filter "name=^sa-" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
    say "backend /health: $(curl -s --max-time 10 "http://127.0.0.1:${BE_PORT}/health" || echo 'no response')"
    say "UI  /: HTTP $(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:${UI_PORT}/" || echo fail)"
}

logs() {
    case "${1:-backend}" in
        opensearch) podman logs --tail 100 "${C_OS}" ;;
        backend)    podman logs --tail 100 "${C_BE}" ;;
        ui)         podman logs --tail 100 "${C_UI}" ;;
        *) echo "logs <opensearch|backend|ui>"; exit 1 ;;
    esac
}

down() {
    for c in "${C_UI}" "${C_BE}" "${C_OS}"; do podman rm -f "${c}" >/dev/null 2>&1 || true; done
    say "Containers removed. Volumes ${V_OS} and ${V_HF} kept."
}

# Daily check of the Sales Manuals: the backend asks the Code Engine scraper for each page, compares the content
# hash with what is indexed and re-indexes only the families that changed. The scraper cannot call us (this box is
# IBM-network only), so a user-level systemd timer does the triggering. Nothing system-wide is touched.
refresh() {
    local dir="${HOME}/.config/systemd/user" url="http://127.0.0.1:${BE_PORT}/api/refresh-manuals"
    case "${1:-status}" in
        install)
            mkdir -p "${dir}"
            cat > "${dir}/sa-manual-refresh.service" <<EOF
[Unit]
Description=Check the IBM Power Sales Manuals for changes and re-index the changed ones

[Service]
Type=oneshot
ExecStart=/usr/bin/curl -sS --max-time 30 -X POST ${url}
EOF
            cat > "${dir}/sa-manual-refresh.timer" <<EOF
[Unit]
Description=Daily check of the IBM Power Sales Manuals

[Timer]
OnCalendar=*-*-* 03:30:00
RandomizedDelaySec=15min
Persistent=true

[Install]
WantedBy=timers.target
EOF
            systemctl --user daemon-reload
            systemctl --user enable --now sa-manual-refresh.timer
            refresh status ;;
        remove)
            systemctl --user disable --now sa-manual-refresh.timer 2>/dev/null || true
            rm -f "${dir}/sa-manual-refresh.service" "${dir}/sa-manual-refresh.timer"
            systemctl --user daemon-reload
            say "Timer removed." ;;
        run)   # refresh run '{"force": true}' | '{"family": "9080-03"}'
            local body="${2:-}"; [[ -n "${body}" ]] || body='{}'
            curl -sS --max-time 30 -X POST -H 'Content-Type: application/json' -d "${body}" "${url}"; echo ;;
        status)
            systemctl --user list-timers sa-manual-refresh.timer --no-pager || true
            curl -sS --max-time 10 "${url}/status" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('last run: started', d['started_at'], 'finished', d['finished_at'], 'running', d['in_progress'])
print('result: ', d['done'], 'of', d['total'], d['counts'])
for r in d['results']:
    if r['status'] != 'unchanged':
        print(' ', r['family'], r['status'], r.get('reason'))
" || true ;;
        *) echo "refresh <install|remove|status|run>"; exit 1 ;;
    esac
}

case "${1:-}" in
    preflight) preflight ;;
    build)     build "${2:-all}" ;;
    up)        up ;;
    status)    status ;;
    logs)      logs "${2:-backend}" ;;
    refresh)   refresh "${2:-status}" "${3:-}" ;;
    down)      down ;;
    *) sed -n '2,25p' "$0"; exit 1 ;;
esac
