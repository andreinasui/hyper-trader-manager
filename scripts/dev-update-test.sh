#!/bin/bash
#
# dev-update-test.sh - Simulate update UI states for local dev compose testing
#
# Writes update-state.json directly into the running hypertrader-api container,
# allowing every update UI state to be tested without running a real update.
#
# Usage:
#   ./scripts/dev-update-test.sh <command>
#   just update-test <command>
#
# Prerequisites (add to environments/dev/api.env):
#   COMPOSE_PROJECT_DIR=/fake-dev-path
#   UPDATE_STATE_DIR=/app/data/update-state
#

set -euo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Config ───────────────────────────────────────────────────────────────────

CONTAINER="hypertrader-api"

# ─── Helpers ──────────────────────────────────────────────────────────────────

info()    { echo -e "  ${CYAN}→${NC}  $*"; }
success() { echo -e "  ${GREEN}✓${NC}  $*"; }
warn()    { echo -e "  ${YELLOW}⚠${NC}  $*"; }
die()     { echo -e "  ${RED}✗${NC}  $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}$*${NC}"; }

hint() {
  echo ""
  echo -e "  ${BLUE}↻${NC}  Refresh the page (or wait 30s) to see the change."
}

# ─── Container helpers ────────────────────────────────────────────────────────

check_container() {
  docker inspect "$CONTAINER" --format '{{.State.Running}}' 2>/dev/null \
    | grep -q "^true$" \
    || die "Container '$CONTAINER' is not running. Start the dev stack first:\n\n     docker compose -f environments/dev/docker-compose.yml --env-file environments/dev/.env up -d"
}

# Reads UPDATE_STATE_DIR from the container's own environment so this script
# stays correct regardless of what's in api.env.
get_state_dir() {
  docker exec "$CONTAINER" sh -c 'echo "${UPDATE_STATE_DIR:-/var/lib/update-state}"'
}

check_update_configured() {
  local configured
  configured=$(docker exec "$CONTAINER" sh -c 'echo "${COMPOSE_PROJECT_DIR:-}"')
  if [[ -z "$configured" ]]; then
    warn "COMPOSE_PROJECT_DIR is not set in the container."
    warn "The update system is disabled (banner will not appear)."
    echo ""
    warn "Add to environments/dev/api.env:"
    echo "     COMPOSE_PROJECT_DIR=/fake-dev-path"
    echo "     UPDATE_STATE_DIR=/app/data/update-state"
    echo ""
    warn "Then rebuild: docker compose -f environments/dev/docker-compose.yml --env-file environments/dev/.env up -d --build api"
    echo ""
  fi
}

write_state() {
  local json="$1"
  local state_dir
  state_dir=$(get_state_dir)
  printf '%s\n' "$json" \
    | docker exec -i "$CONTAINER" sh -c "mkdir -p '$state_dir' && cat > '$state_dir/update-state.json'"
}

show_state() {
  local state_dir
  state_dir=$(get_state_dir)
  local state_file="$state_dir/update-state.json"
  if docker exec "$CONTAINER" test -f "$state_file" 2>/dev/null; then
    docker exec "$CONTAINER" cat "$state_file"
  else
    echo "  (no state file — treated as idle/unconfigured)"
  fi
}

# ─── Commands ─────────────────────────────────────────────────────────────────

cmd_status() {
  check_container
  header "Current update state"
  show_state
  echo ""
}

cmd_update_available() {
  check_container
  check_update_configured
  info "Setting state → update available  (0.0.1 → v99.0.0)"
  write_state '{
  "status": "idle",
  "current_version": "0.0.1",
  "latest_version": "v99.0.0",
  "last_checked": null,
  "update_started_at": null,
  "old_api_image": null,
  "old_web_image": null,
  "new_api_image": null,
  "new_web_image": null,
  "error_message": null,
  "finished_at": null
}'
  success "Banner: \"Update available\" with Update now / Dismiss buttons"
  hint
}

cmd_updating() {
  check_container
  check_update_configured
  info "Setting state → updating"
  write_state '{
  "status": "updating",
  "current_version": "0.0.1",
  "latest_version": "v99.0.0",
  "last_checked": null,
  "update_started_at": null,
  "old_api_image": null,
  "old_web_image": null,
  "new_api_image": null,
  "new_web_image": null,
  "error_message": null,
  "finished_at": null
}'
  success "Overlay: \"Applying update…\" with spinner and progress steps"
  hint
}

cmd_done() {
  check_container
  check_update_configured
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  info "Setting state → idle + recent finished_at ($now)"
  write_state "{
  \"status\": \"idle\",
  \"current_version\": \"99.0.0\",
  \"latest_version\": \"v99.0.0\",
  \"last_checked\": null,
  \"update_started_at\": null,
  \"old_api_image\": null,
  \"old_web_image\": null,
  \"new_api_image\": null,
  \"new_web_image\": null,
  \"error_message\": null,
  \"finished_at\": \"$now\"
}"
  success "Overlay: \"Update complete!\" — will auto-redirect to / after 2s"
  hint
}

cmd_failed() {
  check_container
  check_update_configured
  info "Setting state → failed"
  write_state '{
  "status": "failed",
  "current_version": "0.0.1",
  "latest_version": "v99.0.0",
  "last_checked": null,
  "update_started_at": null,
  "old_api_image": null,
  "old_web_image": null,
  "new_api_image": null,
  "new_web_image": null,
  "error_message": "Docker pull failed: manifest not found",
  "finished_at": null
}'
  success "Overlay: \"Update failed\" with error message and Go home link"
  hint
}

cmd_rolled_back() {
  check_container
  check_update_configured
  info "Setting state → rolled_back"
  write_state '{
  "status": "rolled_back",
  "current_version": "0.0.1",
  "latest_version": "v99.0.0",
  "last_checked": null,
  "update_started_at": null,
  "old_api_image": null,
  "old_web_image": null,
  "new_api_image": null,
  "new_web_image": null,
  "error_message": null,
  "finished_at": null
}'
  success "Overlay: \"Update rolled back\" with Go home link"
  hint
}

cmd_reset() {
  check_container
  local state_dir
  state_dir=$(get_state_dir)
  info "Removing state file"
  docker exec "$CONTAINER" rm -f "$state_dir/update-state.json"
  success "State cleared — banner will disappear on next poll"
  hint
}

# ─── Usage ───────────────────────────────────────────────────────────────────

usage() {
  cat <<EOF

${BOLD}dev-update-test${NC} — Simulate update UI states for local dev compose testing

${BOLD}Usage:${NC}
  ./scripts/dev-update-test.sh <command>
  just update-test <command>

${BOLD}Commands:${NC}
  ${CYAN}status${NC}            Show current update-state.json
  ${CYAN}update-available${NC}  Idle + fake version available   → "Update available" banner
  ${CYAN}updating${NC}          In-progress update              → "Applying update…" overlay
  ${CYAN}done${NC}              Idle + recent finished_at       → "Update complete!" → redirect
  ${CYAN}failed${NC}            Failed update                   → "Update failed" overlay
  ${CYAN}rolled-back${NC}       Rolled-back update              → "Update rolled back" overlay
  ${CYAN}reset${NC}             Remove state file (clean slate)

${BOLD}Typical test flow:${NC}
  just update-test update-available   # 1. see the banner
  just update-test updating           # 2. click "Update now" → see overlay
  just update-test done               # 3. overlay completes → redirects to /
  just update-test reset              # 4. clean up

${BOLD}One-time setup${NC} (add to environments/dev/api.env):
  COMPOSE_PROJECT_DIR=/fake-dev-path
  UPDATE_STATE_DIR=/app/data/update-state

  Then rebuild: docker compose -f environments/dev/docker-compose.yml \\
    --env-file environments/dev/.env up -d --build api

EOF
}

# ─── Dispatch ─────────────────────────────────────────────────────────────────

case "${1:-}" in
  status)           cmd_status ;;
  update-available) cmd_update_available ;;
  updating)         cmd_updating ;;
  done)             cmd_done ;;
  failed)           cmd_failed ;;
  rolled-back)      cmd_rolled_back ;;
  reset)            cmd_reset ;;
  -h|--help|help)   usage; exit 0 ;;
  "")               usage; exit 0 ;;
  *)                die "Unknown command: '$1'. Run with --help for usage." ;;
esac
