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

# Test 5: fetch_manifest accepts a valid manifest, rejects malformed JSON
GOOD="$TEST_TMP/good.json"
cat > "$GOOD" <<'EOF'
{"version":"0.2.7","files":[{"path":"a","source":"b","sha256":"x","mode":"0644","owner":"user"}],"env_schemas":[]}
EOF
# Use file:// URL to avoid network in tests
fetch_manifest "file://$GOOD" "$TEST_TMP/m.json" || fail "fetch_manifest rejected good manifest"
[ "$(manifest_version "$TEST_TMP/m.json")" = "0.2.7" ] || fail "manifest_version"
pass "fetch_manifest accepts valid manifest"

BAD="$TEST_TMP/bad.json"
echo 'not json' > "$BAD"
if fetch_manifest "file://$BAD" "$TEST_TMP/m2.json" 2>/dev/null; then
  fail "fetch_manifest accepted invalid manifest"
fi
pass "fetch_manifest rejects invalid manifest"

# Test 6: manifest_files / manifest_env_schemas produce TSV
got=$(manifest_files "$GOOD" | wc -l)
[ "$got" = "1" ] || fail "manifest_files count: got=$got"
pass "manifest_files emits TSV"

# Test 7: file_sha256 returns empty for missing file, hash for present
[ -z "$(file_sha256 "$TEST_TMP/missing")" ] || fail "file_sha256 missing not empty"
echo "hello" > "$TEST_TMP/h"
[ -n "$(file_sha256 "$TEST_TMP/h")" ] || fail "file_sha256 present empty"
pass "file_sha256 missing/present"

# Test 8: merge_env_file appends missing keys, preserves comments,
# never touches existing keys
ENV_CUR="$TEST_TMP/.env-merge"
ENV_EX="$TEST_TMP/.env.example"
cat > "$ENV_CUR" <<'EOF'
EXISTING=user-edited-value
ANOTHER=keep-me
EOF
cat > "$ENV_EX" <<'EOF'
# Existing key, must NOT be overwritten
EXISTING=default
# A new key
NEW_KEY=new-default
NEW_BARE=42
EOF
merge_env_file "$ENV_CUR" "$ENV_EX"
[ "$(grep ^EXISTING= "$ENV_CUR")" = "EXISTING=user-edited-value" ] || fail "existing key overwritten"
grep -q '^# A new key$' "$ENV_CUR" || fail "comment for new key not preserved"
grep -q '^NEW_KEY=new-default$' "$ENV_CUR" || fail "new key not appended"
grep -q '^NEW_BARE=42$' "$ENV_CUR" || fail "bare new key not appended"
pass "merge_env_file appends + preserves"

# Test 9: env_missing_keys reports correctly
got=$(env_missing_keys "$ENV_CUR" "$ENV_EX" | sort | tr '\n' ' ')
[ "$got" = "" ] || fail "expected no missing keys after merge, got=$got"
pass "env_missing_keys post-merge empty"

# Test 10: merge on missing current file copies example
ENV_NEW="$TEST_TMP/.env-new"
merge_env_file "$ENV_NEW" "$ENV_EX"
[ -f "$ENV_NEW" ] || fail "merge_env_file did not create file"
grep -q '^EXISTING=default$' "$ENV_NEW" || fail "merge_env_file did not copy example"
pass "merge_env_file creates from example when missing"

# Test 11: snapshot_create + snapshot_restore round-trip on a small dir
SNAP_PD="$TEST_TMP/pd"
mkdir -p "$SNAP_PD/traefik/dynamic" "$SNAP_PD/bin"
echo "compose-v1" > "$SNAP_PD/docker-compose.yml"
echo "traefik-v1" > "$SNAP_PD/traefik/traefik.yml"
echo "boot-v1"    > "$SNAP_PD/traefik/dynamic/00-bootstrap.yml"
echo "manager-v1" > "$SNAP_PD/bin/hyper-trader-manager"
echo "ENV=v1"     > "$SNAP_PD/.env"
echo '{"version":"0.1.0","files":[],"env_schemas":[]}' > "$SNAP_PD/manifest.json"

# Snapshot using legacy fallback (empty current manifest)
backup=$(snapshot_create "$SNAP_PD" "0.1.0" "")
[ -d "$backup" ] || fail "backup dir not created"
[ -f "$backup/docker-compose.yml" ] || fail "compose not snapshotted"
[ -f "$backup/traefik/traefik.yml" ] || fail "traefik not snapshotted"
[ -f "$backup/bin/hyper-trader-manager" ] || fail "manager not snapshotted"
[ -f "$backup/.env" ] || fail ".env not snapshotted"
[ -f "$backup/manifest.json" ] || fail "manifest not snapshotted"
pass "snapshot_create captures legacy file set"

# Mutate, then restore, expect originals back
echo "compose-v2" > "$SNAP_PD/docker-compose.yml"
rm "$SNAP_PD/traefik/traefik.yml"
snapshot_restore "$SNAP_PD" "$backup"
[ "$(cat "$SNAP_PD/docker-compose.yml")" = "compose-v1" ] || fail "compose not restored"
[ "$(cat "$SNAP_PD/traefik/traefik.yml")" = "traefik-v1" ] || fail "traefik not restored"
pass "snapshot_restore round-trip"

# Test 12: snapshot_prune keeps N most recent
PRUNE_PD="$TEST_TMP/prune"
mkdir -p "$PRUNE_PD/.backup"
for v in 0.1.0 0.1.1 0.1.2 0.1.3 0.1.4; do
  mkdir -p "$PRUNE_PD/.backup/$v"
  touch -d "$(date -d "$v days ago" 2>/dev/null || date)" "$PRUNE_PD/.backup/$v" 2>/dev/null || true
done
# Make mtimes monotonically increasing in name order
for v in 0.1.0 0.1.1 0.1.2 0.1.3 0.1.4; do
  touch "$PRUNE_PD/.backup/$v"
  sleep 0.01
done
snapshot_prune "$PRUNE_PD" 3
remaining=$(find "$PRUNE_PD/.backup" -mindepth 1 -maxdepth 1 -type d | wc -l)
[ "$remaining" = "3" ] || fail "snapshot_prune kept $remaining, expected 3"
[ -d "$PRUNE_PD/.backup/0.1.4" ] || fail "newest pruned"
[ -d "$PRUNE_PD/.backup/0.1.3" ] || fail "2nd-newest pruned"
[ -d "$PRUNE_PD/.backup/0.1.2" ] || fail "3rd-newest pruned"
[ ! -d "$PRUNE_PD/.backup/0.1.1" ] || fail "0.1.1 should be pruned"
pass "snapshot_prune keeps N most recent"

# Test 13: apply_managed_file downloads and verifies checksum
SRC_DIR="$TEST_TMP/src"
DST_DIR="$TEST_TMP/dst"
mkdir -p "$SRC_DIR/sub" "$DST_DIR"
echo "hello-world" > "$SRC_DIR/sub/file.txt"
expected=$(sha256sum "$SRC_DIR/sub/file.txt" | awk '{print $1}')
apply_managed_file "$DST_DIR" "file://$SRC_DIR" "sub/file.txt" "out/file.txt" "$expected" "0644" "user"
[ "$(cat "$DST_DIR/out/file.txt")" = "hello-world" ] || fail "file not written"
[ "$(stat -c '%a' "$DST_DIR/out/file.txt")" = "644" ] || fail "mode not applied"
pass "apply_managed_file good path"

# Test 14: checksum mismatch refuses to write
if apply_managed_file "$DST_DIR" "file://$SRC_DIR" "sub/file.txt" "bad/file.txt" "deadbeef" "0644" "user" 2>/dev/null; then
  fail "apply_managed_file accepted bad checksum"
fi
[ ! -f "$DST_DIR/bad/file.txt" ] || fail "bad checksum left a file behind"
pass "apply_managed_file rejects bad checksum"

# Test 15: migrate_legacy_layout moves real script and creates symlink
# (Use a fake "system path" within TEST_TMP to avoid touching /usr/local/bin.)
MIG_PD="$TEST_TMP/mig"
mkdir -p "$MIG_PD"
FAKE_LINK="$TEST_TMP/fake-usr-local-bin/hyper-trader-manager"
mkdir -p "$(dirname "$FAKE_LINK")"
echo "#!/bin/sh" > "$FAKE_LINK"
echo "echo legacy" >> "$FAKE_LINK"
chmod +x "$FAKE_LINK"

# Wrapper that accepts an explicit link path (for testability)
migrate_legacy_layout_with_link() {
  local pd="$1" link="$2"
  local target="${pd}/bin/hyper-trader-manager"
  [[ -f "$target" ]] && return 0
  mkdir -p "${pd}/bin"
  if [[ -f "$link" && ! -L "$link" ]]; then
    cp -a "$link" "$target"
    chmod 0755 "$target"
    rm -f "$link"
    ln -sf "$target" "$link"
  fi
}

migrate_legacy_layout_with_link "$MIG_PD" "$FAKE_LINK"
[ -f "$MIG_PD/bin/hyper-trader-manager" ] || fail "script not moved into bin/"
[ -L "$FAKE_LINK" ] || fail "symlink not created"
[ "$(readlink "$FAKE_LINK")" = "$MIG_PD/bin/hyper-trader-manager" ] \
  || fail "symlink target wrong"
pass "legacy-layout migration"

echo "All helper unit tests passed."
