#!/usr/bin/env bash
# Pure-bash unit tests for update-helper.sh helper functions.
# Run: bash helper/test-update-helper.sh
set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=update-helper.sh
[[ -f "$THIS_DIR/update-helper.sh" ]] || { echo "FAIL: update-helper.sh not found — implement it first" >&2; exit 1; }
source "$THIS_DIR/update-helper.sh"

TEST_TMP="$(mktemp -d)"
trap 'rm -rf "$TEST_TMP"' EXIT

STATE_FILE="$TEST_TMP/update-state.json"
echo '{"status":"idle","current_version":"0.1.1","latest_version":"0.1.2","last_checked":null,"update_started_at":null,"old_api_image":null,"old_web_image":null,"new_api_image":null,"new_web_image":null,"error_message":null,"finished_at":null}' > "$STATE_FILE"

fail() { echo "FAIL: $1" >&2; exit 1; }
pass() { echo "PASS: $1"; }

# Test 1: write_state updates a single field
# write_state reads STATE_FILE from env
STATE_FILE="$STATE_FILE" write_state status updating
got=$(jq -r .status "$STATE_FILE")
[ "$got" = "updating" ] || fail "expected status=updating, got=$got"
pass "write_state updates status"

# Test 2: write_state updates multiple fields atomically
# write_state reads STATE_FILE from env
STATE_FILE="$STATE_FILE" write_state error_message "boom" finished_at "2026-05-03T00:00:00Z"
[ "$(jq -r .error_message "$STATE_FILE")" = "boom" ] || fail "error_message"
[ "$(jq -r .finished_at "$STATE_FILE")" = "2026-05-03T00:00:00Z" ] || fail "finished_at"
pass "write_state multi-field"

# Test 3: rewrite_env replaces existing keys, preserves comments + unrelated keys
ENV_FILE="$TEST_TMP/.env"
cat > "$ENV_FILE" <<'EOF'
# A comment
HYPERTRADER_API_IMAGE=ghcr.io/foo/api:0.1.1
HYPERTRADER_WEB_IMAGE=ghcr.io/foo/web:0.1.1
DOCKER_SOCK=/var/run/docker.sock
EOF
ENV_FILE="$ENV_FILE" rewrite_env "ghcr.io/foo/api:0.1.2" "ghcr.io/foo/web:0.1.2"
grep -q '^# A comment$' "$ENV_FILE" || fail "comment preserved"
grep -q '^DOCKER_SOCK=/var/run/docker.sock$' "$ENV_FILE" || fail "unrelated key preserved"
grep -q '^HYPERTRADER_API_IMAGE=ghcr.io/foo/api:0.1.2$' "$ENV_FILE" || fail "api image rewritten"
grep -q '^HYPERTRADER_WEB_IMAGE=ghcr.io/foo/web:0.1.2$' "$ENV_FILE" || fail "web image rewritten"
pass "rewrite_env preserves comments + unrelated keys"

# Test 4: rewrite_env appends keys when missing
ENV_FILE2="$TEST_TMP/.env2"
echo "OTHER=1" > "$ENV_FILE2"
ENV_FILE="$ENV_FILE2" rewrite_env "ghcr.io/foo/api:0.1.2" "ghcr.io/foo/web:0.1.2"
grep -q '^HYPERTRADER_API_IMAGE=ghcr.io/foo/api:0.1.2$' "$ENV_FILE2" || fail "appended api"
grep -q '^HYPERTRADER_WEB_IMAGE=ghcr.io/foo/web:0.1.2$' "$ENV_FILE2" || fail "appended web"
pass "rewrite_env appends missing keys"

echo "All helper unit tests passed."
