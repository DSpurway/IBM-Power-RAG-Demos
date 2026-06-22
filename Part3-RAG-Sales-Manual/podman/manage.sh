#!/bin/bash
# =============================================================================
# manage.sh — Day-to-day management of the RAG Demo Podman stack
# =============================================================================
# Usage:
#   ./manage.sh start              # start all services
#   ./manage.sh stop               # stop all services
#   ./manage.sh restart            # stop then start
#   ./manage.sh restart <service>  # restart one service (e.g. rag-backend)
#   ./manage.sh status             # show health of all services
#   ./manage.sh logs <service>     # tail logs (service: opensearch|vllm|rag-backend|carbon-ui)
#   ./manage.sh rebuild <service>  # rebuild one image and restart that service
#   ./manage.sh ps                 # podman-compose ps
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Two levels up from Part3-RAG-Sales-Manual/podman/ to reach the repo root
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✗${NC}  $*"; }
info() { echo -e "  ${BLUE}ℹ${NC}  $*"; }

cd "${SCRIPT_DIR}"

# Resolve the container name for a given service alias
container_name() {
    case "$1" in
        opensearch)   echo "opensearch-service" ;;
        vllm)         echo "vllm-service" ;;
        rag-backend)  echo "rag-backend" ;;
        carbon-ui)    echo "carbon-rag-ui" ;;
        *)            echo "$1" ;;   # pass through as-is
    esac
}

# Map service alias to build context and image name
build_info() {
    case "$1" in
        rag-backend)
            echo "${REPO_ROOT}/Part3-RAG-Sales-Manual/rag-backend localhost/rag-backend:latest"
            ;;
        carbon-ui)
            echo "${REPO_ROOT}/Part3-RAG-Sales-Manual/carbon-rag-ui localhost/carbon-rag-ui:latest"
            ;;
        *)
            echo ""
            ;;
    esac
}

# ── status ────────────────────────────────────────────────────────────────────
cmd_status() {
    local fqdn
    fqdn=$(hostname -f 2>/dev/null || hostname)

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BOLD}${CYAN}  RAG Demo — Service Status${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    declare -A PORTS=( [opensearch-service]=9200 [vllm-service]=8000 [rag-backend]=8080 [carbon-rag-ui]=3000 )
    declare -A HEALTH_PATH=( [opensearch-service]="/_cluster/health" [vllm-service]="/health"
                              [rag-backend]="/health" [carbon-rag-ui]="/" )

    local all_ok=true

    for svc in opensearch-service vllm-service rag-backend carbon-rag-ui; do
        local port="${PORTS[$svc]}"
        local path="${HEALTH_PATH[$svc]}"

        # Podman container state
        local state
        state=$(podman inspect --format '{{.State.Status}}' "${svc}" 2>/dev/null || echo "not found")

        printf "  %-20s  " "${svc}"

        if [[ "${state}" == "running" ]]; then
            # HTTP health check
            if curl -sf "http://localhost:${port}${path}" &>/dev/null; then
                echo -e "${GREEN}running  ✓${NC}   http://${fqdn}:${port}"
            else
                echo -e "${YELLOW}running (no HTTP yet)${NC}   port ${port}"
                all_ok=false
            fi
        elif [[ "${state}" == "not found" ]]; then
            echo -e "${RED}not created${NC}"
            all_ok=false
        else
            echo -e "${RED}${state}${NC}"
            all_ok=false
        fi
    done

    echo ""
    if $all_ok; then
        ok "All services healthy"
    else
        warn "Some services need attention — run: ./manage.sh logs <service>"
    fi
    echo ""
}

# ── start ─────────────────────────────────────────────────────────────────────
cmd_start() {
    echo -e "${BOLD}Starting all services…${NC}"
    podman-compose --env-file .env up -d
    ok "Services started"
    cmd_status
}

# ── stop ──────────────────────────────────────────────────────────────────────
cmd_stop() {
    echo -e "${BOLD}Stopping all services…${NC}"
    podman-compose --env-file .env down
    ok "Services stopped"
}

# ── restart ───────────────────────────────────────────────────────────────────
cmd_restart() {
    local svc="${1:-}"
    if [[ -n "${svc}" ]]; then
        local cname
        cname=$(container_name "${svc}")
        echo -e "${BOLD}Restarting ${cname}…${NC}"
        podman restart "${cname}"
        ok "${cname} restarted"
    else
        cmd_stop
        cmd_start
    fi
}

# ── logs ──────────────────────────────────────────────────────────────────────
cmd_logs() {
    local svc="${1:-}"
    if [[ -z "${svc}" ]]; then
        err "Usage: ./manage.sh logs <service>"
        echo "  Services: opensearch | vllm | rag-backend | carbon-ui"
        exit 1
    fi
    local cname
    cname=$(container_name "${svc}")
    echo -e "${BLUE}Tailing logs for ${cname} (Ctrl-C to stop)…${NC}"
    podman logs -f "${cname}"
}

# ── rebuild ───────────────────────────────────────────────────────────────────
cmd_rebuild() {
    local svc="${1:-}"
    if [[ -z "${svc}" ]]; then
        err "Usage: ./manage.sh rebuild <service>"
        echo "  Rebuildable services: rag-backend | carbon-ui"
        exit 1
    fi

    local build_args
    build_args=$(build_info "${svc}")
    if [[ -z "${build_args}" ]]; then
        err "Service '${svc}' does not have a local build context (it uses a pre-built image)."
        exit 1
    fi

    local ctx img
    ctx=$(echo "${build_args}" | cut -d' ' -f1)
    img=$(echo "${build_args}" | cut -d' ' -f2)

    echo -e "${BOLD}Rebuilding ${img} from ${ctx}…${NC}"
    podman build --tag "${img}" "${ctx}"
    ok "${img} rebuilt"

    local cname
    cname=$(container_name "${svc}")
    echo -e "${BOLD}Restarting ${cname}…${NC}"
    podman restart "${cname}"
    ok "${cname} restarted with new image"
}

# ── ps ────────────────────────────────────────────────────────────────────────
cmd_ps() {
    podman-compose --env-file .env ps
}

# ── dispatch ──────────────────────────────────────────────────────────────────
CMD="${1:-status}"
shift || true

case "${CMD}" in
    start)    cmd_start ;;
    stop)     cmd_stop ;;
    restart)  cmd_restart "$@" ;;
    status)   cmd_status ;;
    logs)     cmd_logs "$@" ;;
    rebuild)  cmd_rebuild "$@" ;;
    ps)       cmd_ps ;;
    *)
        echo "Usage: ./manage.sh {start|stop|restart [svc]|status|logs <svc>|rebuild <svc>|ps}"
        exit 1
        ;;
esac

# Made with Bob
