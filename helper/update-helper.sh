#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="${STATE_FILE:-/var/lib/update-state/update-state.json}"
ENV_FILE="${ENV_FILE:-${COMPOSE_PROJECT_DIR:-}/.env}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-60}"
API_CONTAINER="${API_CONTAINER:-hypertrader-api}"
WEB_CONTAINER="${WEB_CONTAINER:-hypertrader-web}"

now() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

write_state() {
  # write_state KEY VAL [KEY VAL...]
  local jq_args=() filter=""
  while [ $# -gt 0 ]; do
    local k="$1" v="$2"; shift 2
    if [ -z "$filter" ]; then filter=".$k = \$$k"; else filter="$filter | .$k = \$$k"; fi
    if [ "$v" = "null" ]; then
      jq_args+=(--argjson "$k" null)
    else
      jq_args+=(--arg "$k" "$v")
    fi
  done
  [ -f "$STATE_FILE" ] || echo '{}' > "$STATE_FILE"
  local tmp; tmp="$(mktemp "$(dirname "$STATE_FILE")/.state.XXXXXX")"
  jq "${jq_args[@]}" "$filter" "$STATE_FILE" > "$tmp"
  mv "$tmp" "$STATE_FILE"
}

rewrite_env() {
  local new_api="$1" new_web="$2"
  local tmp; tmp="$(mktemp)"
  local saw_api=0 saw_web=0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      HYPERTRADER_API_IMAGE=*)
        echo "HYPERTRADER_API_IMAGE=$new_api" >> "$tmp"; saw_api=1 ;;
      HYPERTRADER_WEB_IMAGE=*)
        echo "HYPERTRADER_WEB_IMAGE=$new_web" >> "$tmp"; saw_web=1 ;;
      *)
        echo "$line" >> "$tmp" ;;
    esac
  done < "$ENV_FILE"
  [ "$saw_api" = 1 ] || echo "HYPERTRADER_API_IMAGE=$new_api" >> "$tmp"
  [ "$saw_web" = 1 ] || echo "HYPERTRADER_WEB_IMAGE=$new_web" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
}

wait_for_healthy() {
  local name="$1" timeout_secs="$2"
  local deadline=$(( $(date +%s) + timeout_secs ))
  local running_since=0
  while [ "$(date +%s)" -lt "$deadline" ]; do
    local health
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo "missing")
    case "$health" in
      healthy) return 0 ;;
      none)
        local state
        state=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "missing")
        if [ "$state" = "running" ]; then
          if [ "$running_since" = 0 ]; then running_since=$(date +%s); fi
          if [ $(( $(date +%s) - running_since )) -ge 10 ]; then return 0; fi
        else
          running_since=0
        fi
        ;;
      *)
        running_since=0
        ;;
    esac
    sleep 2
  done
  return 1
}

# Main flow — only runs when executed directly, not sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  : "${COMPOSE_PROJECT_DIR:?COMPOSE_PROJECT_DIR is required}"
  : "${OLD_API_IMAGE:?OLD_API_IMAGE is required}"
  : "${OLD_WEB_IMAGE:?OLD_WEB_IMAGE is required}"
  : "${NEW_API_IMAGE:?NEW_API_IMAGE is required}"
  : "${NEW_WEB_IMAGE:?NEW_WEB_IMAGE is required}"

  write_state status updating update_started_at "$(now)" \
    old_api_image "$OLD_API_IMAGE" old_web_image "$OLD_WEB_IMAGE" \
    new_api_image "$NEW_API_IMAGE" new_web_image "$NEW_WEB_IMAGE"

  cd "$COMPOSE_PROJECT_DIR"

  echo "[helper] update started: $OLD_API_IMAGE -> $NEW_API_IMAGE"
  rewrite_env "$NEW_API_IMAGE" "$NEW_WEB_IMAGE"

  docker compose down --timeout 30
  docker compose up -d

  if wait_for_healthy "$API_CONTAINER" "$HEALTH_TIMEOUT_SECONDS" \
     && wait_for_healthy "$WEB_CONTAINER" "$HEALTH_TIMEOUT_SECONDS"; then
    write_state status idle finished_at "$(now)" error_message null
    echo "[helper] update succeeded"
    exit 0
  fi

  echo "[helper] new version unhealthy — rolling back"
  write_state error_message "health check timeout"
  rewrite_env "$OLD_API_IMAGE" "$OLD_WEB_IMAGE"
  docker compose down --timeout 30
  docker compose up -d

  if wait_for_healthy "$API_CONTAINER" "$HEALTH_TIMEOUT_SECONDS" \
     && wait_for_healthy "$WEB_CONTAINER" "$HEALTH_TIMEOUT_SECONDS"; then
    write_state status rolled_back finished_at "$(now)" error_message "new version failed health check"
    echo "[helper] rolled back successfully"
    exit 0
  fi

  write_state status failed finished_at "$(now)" error_message "rollback also failed - manual intervention required"
  echo "[helper] catastrophic failure"
  exit 1
fi
