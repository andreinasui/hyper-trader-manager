#!/usr/bin/env bash
# =============================================================================
# hyper-trader-manager — manage the HyperTrader Manager stack
# =============================================================================
# Usage:
#   hyper-trader-manager <command> [args]
#
# Commands:
#   start    Pull images and start all containers
#   stop     Stop and remove all containers
#   restart  Stop then start
#   status   Show running container status
#   logs     Follow logs (optionally filter by service name)
#   update   Pull new images and restart
#
# Examples:
#   hyper-trader-manager start
#   hyper-trader-manager logs api
#   hyper-trader-manager update
# =============================================================================
set -euo pipefail

# Resolve INSTALL_DIR from this script's real path, so it works whether invoked
# directly (/opt/hyper-trader/bin/hyper-trader-manager) or via the symlink in
# /usr/local/bin/. Falls back to the well-known path for legacy installs.
SELF="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SELF_DIR="$(cd "$(dirname "$SELF")" && pwd)"
if [[ "$(basename "$SELF_DIR")" == "bin" ]]; then
  INSTALL_DIR="$(dirname "$SELF_DIR")"
else
  INSTALL_DIR="/opt/hyper-trader"
fi
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

die() { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ── Resolve compose command ───────────────────────────────────────────────────
if docker compose version &>/dev/null 2>&1; then
    compose() { docker compose "$@"; }
elif command -v docker-compose &>/dev/null; then
    compose() { docker-compose "$@"; }
else
    die "Neither 'docker compose' plugin nor 'docker-compose' standalone was found."
fi

[[ -f "${COMPOSE_FILE}" ]] || die "Compose file not found: ${COMPOSE_FILE}\nIs HyperTrader Manager installed?"

# ── Commands ──────────────────────────────────────────────────────────────────
cmd_start() {
    echo -e "${BLUE}Starting HyperTrader Manager...${RESET}"
    compose -f "${COMPOSE_FILE}" up -d --pull always
    echo -e "${GREEN}Started.${RESET}"
}

cmd_stop() {
    echo -e "${BLUE}Stopping HyperTrader Manager...${RESET}"
    compose -f "${COMPOSE_FILE}" down
    echo -e "${GREEN}Stopped.${RESET}"
}

cmd_restart() {
    cmd_stop
    cmd_start
}

cmd_status() {
    compose -f "${COMPOSE_FILE}" ps
}

cmd_logs() {
    # pass remaining args as service filter (e.g. hyper-trader-manager logs api)
    compose -f "${COMPOSE_FILE}" logs -f --tail=100 "${@}"
}

cmd_update() {
    echo -e "${BLUE}Pulling latest images...${RESET}"
    compose -f "${COMPOSE_FILE}" pull
    echo -e "${BLUE}Restarting containers...${RESET}"
    compose -f "${COMPOSE_FILE}" up -d
    echo -e "${GREEN}Update complete.${RESET}"
}

cmd_restore_backup() {
    local version="${1:-}"
    [[ -n "$version" ]] || die "Usage: hyper-trader-manager restore-backup <version>"

    local backup="${INSTALL_DIR}/.backup/${version}"
    [[ -d "$backup" ]] || die "Backup not found: ${backup}\nAvailable: $(ls "${INSTALL_DIR}/.backup" 2>/dev/null || echo none)"

    echo -e "${YELLOW}Restoring from backup ${version}...${RESET}"
    echo -e "${BLUE}This will stop the stack, copy ${backup} over ${INSTALL_DIR}, and restart.${RESET}"
    read -r -p "Continue? [y/N] " confirm
    [[ "$confirm" =~ ^[yY]$ ]] || { echo "Aborted."; exit 1; }

    compose -f "${COMPOSE_FILE}" down --timeout 30 || true
    cp -a "${backup}/." "${INSTALL_DIR}/"
    compose -f "${COMPOSE_FILE}" up -d
    echo -e "${GREEN}Restored.${RESET}"
}

usage() {
    echo -e "${BOLD}Usage:${RESET} hyper-trader-manager <command> [args]"
    echo ""
    echo -e "${BOLD}Commands:${RESET}"
    echo "  start    Pull images and start all containers"
    echo "  stop     Stop and remove all containers"
    echo "  restart  Stop then start"
    echo "  status   Show running container status"
    echo "  logs     Follow logs [service]"
    echo "  update   Pull new images and restart"
    echo "  restore-backup <version>  Restore host files from .backup/<version>/"
}

case "${1:-}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    logs)    shift; cmd_logs "$@" ;;
    update)  cmd_update ;;
    restore-backup) shift; cmd_restore_backup "$@" ;;
    *)       usage; exit 1 ;;
esac
