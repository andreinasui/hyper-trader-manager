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

# ─── Manifest helpers ─────────────────────────────────────────────────────────

# fetch_manifest URL DEST
# Downloads a manifest JSON to DEST. Validates it parses and has required
# top-level fields. Returns 0 on success, non-zero on failure.
fetch_manifest() {
  local url="$1" dest="$2"
  curl -fsSL "$url" -o "$dest" || return 1
  jq -e '.version and (.files|type=="array") and (.env_schemas|type=="array")' "$dest" >/dev/null \
    || return 1
}

# manifest_files MANIFEST  → emits each file entry as:
#   path<TAB>source<TAB>sha256<TAB>mode<TAB>owner
manifest_files() {
  jq -r '.files[] | [.path, .source, .sha256, .mode, .owner] | @tsv' "$1"
}

# manifest_env_schemas MANIFEST → emits:
#   path<TAB>source
manifest_env_schemas() {
  jq -r '.env_schemas[] | [.path, .source] | @tsv' "$1"
}

# manifest_version MANIFEST
manifest_version() { jq -r '.version' "$1"; }

# file_sha256 PATH
# Returns sha256 of file, or empty string if file missing.
file_sha256() {
  [[ -f "$1" ]] || { echo ""; return 0; }
  sha256sum "$1" | awk '{print $1}'
}

# ─── Env merge ────────────────────────────────────────────────────────────────

# merge_env_file CURRENT NEW_EXAMPLE
# For each KEY=VALUE line in NEW_EXAMPLE that has no matching ^KEY= line in
# CURRENT, append the entire example line (and its immediately preceding
# comment lines, if any) to CURRENT. Existing keys are left untouched.
# Lines that aren't KEY=VAL or comments are skipped.
merge_env_file() {
  local current="$1" example="$2"
  [[ -f "$current" ]] || { cp "$example" "$current"; return 0; }

  local pending_comments="" line key
  local appended=0
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line//[[:space:]]/}" ]]; then
      pending_comments+="$line"$'\n'
      continue
    fi
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]]; then
      key="${BASH_REMATCH[1]}"
      if grep -q "^${key}=" "$current"; then
        pending_comments=""
        continue
      fi
      # Append, preceded by any pending comments. Add a leading blank line
      # to separate from existing content, but only on the first append.
      if [[ "$appended" -eq 0 ]]; then
        printf '\n' >> "$current"
        appended=1
      fi
      [[ -n "$pending_comments" ]] && printf '%s' "$pending_comments" >> "$current"
      printf '%s\n' "$line" >> "$current"
      pending_comments=""
    else
      pending_comments=""
    fi
  done < "$example"
}

# env_missing_keys CURRENT NEW_EXAMPLE → list of keys in example missing in current
env_missing_keys() {
  local current="$1" example="$2"
  local line key
  while IFS= read -r line || [ -n "$line" ]; do
    [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]] || continue
    key="${BASH_REMATCH[1]}"
    if ! grep -q "^${key}=" "$current" 2>/dev/null; then
      echo "$key"
    fi
  done < "$example"
}

# ─── Snapshot ─────────────────────────────────────────────────────────────────

# snapshot_create PROJECT_DIR OLD_VERSION CUR_MANIFEST
# Creates ${PROJECT_DIR}/.backup/${OLD_VERSION}/ and copies into it:
#  - every file listed in CUR_MANIFEST (or, if CUR_MANIFEST is empty/missing,
#    the legacy default list);
#  - the current manifest.json (if present);
#  - .env and api.env.
# Echoes the backup directory on success.
snapshot_create() {
  local pd="$1" old="$2" cur_manifest="$3"
  [[ -n "$old" ]] || return 1  # guard: empty version would rm -rf the entire .backup/ dir
  local backup="${pd}/.backup/${old}"
  rm -rf "$backup"
  mkdir -p "$backup"

  local paths=()
  if [[ -n "$cur_manifest" && -f "$cur_manifest" ]]; then
    while IFS=$'\t' read -r path _ _ _ _; do
      paths+=("$path")
    done < <(manifest_files "$cur_manifest")
  else
    # Legacy default list (first run, no prior manifest)
    paths=("docker-compose.yml" "traefik" "bin/hyper-trader-manager")
  fi

  local p src dst
  for p in "${paths[@]}"; do
    src="${pd}/${p}"
    dst="${backup}/${p}"
    [[ -e "$src" ]] || continue
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
  done

  # Always snapshot manifest.json + env files if they exist
  for f in manifest.json .env api.env; do
    [[ -e "${pd}/${f}" ]] && cp -a "${pd}/${f}" "${backup}/${f}"
  done

  echo "$backup"
}

# snapshot_restore PROJECT_DIR BACKUP_DIR
# Copies everything from BACKUP_DIR back over PROJECT_DIR, preserving modes.
snapshot_restore() {
  local pd="$1" backup="$2"
  [[ -d "$backup" ]] || return 1
  # cp -a copies dirs recursively, preserves mode/ownership.
  # We use a trailing /. to copy contents, not the directory itself.
  cp -a "${backup}/." "${pd}/"
}

# snapshot_prune PROJECT_DIR KEEP_N
# Keeps the KEEP_N most recently modified directories under .backup/, deletes the rest.
snapshot_prune() {
  local pd="$1" keep="$2"
  local d="${pd}/.backup"
  [[ -d "$d" ]] || return 0
  # List dirs sorted by mtime descending, skip first KEEP_N, rm -rf the rest.
  local i=0
  while IFS= read -r -d '' dir; do
    i=$((i+1))
    if (( i > keep )); then
      rm -rf "$dir"
    fi
  done < <(find "$d" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\0' \
            | sort -zrn | sed -z 's/^[^ ]* //')
}

# ─── File replace ─────────────────────────────────────────────────────────────

# resolve_owner OWNER_TAG PROJECT_DIR
# "user"     → returns "<uid>:<gid>" of PROJECT_DIR (preserves install-time owner)
# "uid:1000" → returns "1000:1000"
resolve_owner() {
  local tag="$1" pd="$2"
  case "$tag" in
    uid:*)
      local n="${tag#uid:}"
      echo "${n}:${n}"
      ;;
    user)
      stat -c '%u:%g' "$pd"
      ;;
    *)
      stat -c '%u:%g' "$pd"
      ;;
  esac
}

# apply_managed_file PROJECT_DIR RAW_BASE SOURCE DEST EXPECTED_SHA MODE OWNER_TAG
# Downloads RAW_BASE/SOURCE, verifies sha256, then atomically moves into
# PROJECT_DIR/DEST with the requested mode and owner.
apply_managed_file() {
  local pd="$1" raw="$2" src="$3" dest="$4" expected="$5" mode="$6" owner_tag="$7"
  local target="${pd}/${dest}"
  local tmp; tmp="$(mktemp "${pd}/.tmp.XXXXXX")"

  curl -fsSL "${raw}/${src}" -o "$tmp" || { rm -f "$tmp"; return 1; }
  local got; got="$(sha256sum "$tmp" | awk '{print $1}')"
  if [[ "$got" != "$expected" ]]; then
    rm -f "$tmp"
    echo "[helper] checksum mismatch: ${dest} (expected ${expected}, got ${got})" >&2
    return 2
  fi

  mkdir -p "$(dirname "$target")"
  chmod "$mode" "$tmp"
  local owner; owner="$(resolve_owner "$owner_tag" "$pd")"
  chown "$owner" "$tmp" 2>/dev/null || true
  mv -f "$tmp" "$target"
 }

# ─── Legacy-layout migration ──────────────────────────────────────────────────

# migrate_legacy_layout PROJECT_DIR
# If /opt/hyper-trader/bin/hyper-trader-manager doesn't exist and
# /usr/local/bin/hyper-trader-manager is a regular file, move it into
# PROJECT_DIR/bin/ and replace /usr/local/bin/... with a symlink.
# Best-effort: failures are warnings, not fatal.
migrate_legacy_layout() {
  local pd="$1"
  local target="${pd}/bin/hyper-trader-manager"
  local link="/usr/local/bin/hyper-trader-manager"

  [[ -f "$target" ]] && return 0  # already migrated

  mkdir -p "${pd}/bin"

  if [[ -f "$link" && ! -L "$link" ]]; then
    cp -a "$link" "$target" || { echo "[helper] WARN: could not migrate manager script: cp failed" >&2; return 0; }
    chmod 0755 "$target"
    rm -f "$link"
    if ! ln -sf "$target" "$link" 2>/dev/null; then
      echo "[helper] WARN: could not create symlink at ${link} — add ${pd}/bin to PATH manually" >&2
    fi
  fi
}

# ─── Main flow ─────────────────────────────────────────────────────────────────
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  : "${COMPOSE_PROJECT_DIR:?COMPOSE_PROJECT_DIR is required}"
  : "${OLD_API_IMAGE:?OLD_API_IMAGE is required}"
  : "${OLD_WEB_IMAGE:?OLD_WEB_IMAGE is required}"
  : "${NEW_API_IMAGE:?NEW_API_IMAGE is required}"
  : "${NEW_WEB_IMAGE:?NEW_WEB_IMAGE is required}"

  # Host-update inputs (optional; absent on legacy callers)
  OLD_VERSION="${OLD_VERSION:-unknown}"
  NEW_VERSION="${NEW_VERSION:-}"
  MANIFEST_URL="${MANIFEST_URL:-}"
  RAW_BASE="${RAW_BASE:-}"

  cd "$COMPOSE_PROJECT_DIR"

  write_state status updating sub_phase null update_started_at "$(now)" \
    old_api_image "$OLD_API_IMAGE" old_web_image "$OLD_WEB_IMAGE" \
    new_api_image "$NEW_API_IMAGE" new_web_image "$NEW_WEB_IMAGE" \
    backup_path null

  echo "[helper] update started: $OLD_API_IMAGE -> $NEW_API_IMAGE (old=$OLD_VERSION new=$NEW_VERSION)"

  HOST_PHASE_RAN=0
  BACKUP_DIR=""

  # ── Phase A + B: host files (if manifest available) ─────────────────────────
  if [[ -n "$MANIFEST_URL" && -n "$RAW_BASE" ]]; then
    NEW_MANIFEST="/tmp/new-manifest.json"
    CUR_MANIFEST="${COMPOSE_PROJECT_DIR}/manifest.json"

    if ! fetch_manifest "$MANIFEST_URL" "$NEW_MANIFEST"; then
      write_state status failed finished_at "$(now)" error_message "manifest fetch failed"
      echo "[helper] manifest fetch failed — aborting" >&2
      exit 1
    fi

    # Plan
    CHANGED_FILES=()
    LOCAL_EDITS=()
    while IFS=$'\t' read -r path src expected mode owner; do
      cur="${COMPOSE_PROJECT_DIR}/${path}"
      cur_sha="$(file_sha256 "$cur")"
      if [[ "$cur_sha" != "$expected" ]]; then
        CHANGED_FILES+=("${path}|${src}|${expected}|${mode}|${owner}")
      fi
      # Detect local edits vs prior manifest (advisory)
      if [[ -f "$CUR_MANIFEST" ]]; then
        prior_sha=$(jq -r --arg p "$path" '.files[]|select(.path==$p)|.sha256 // empty' "$CUR_MANIFEST")
        if [[ -n "$prior_sha" && -n "$cur_sha" && "$cur_sha" != "$prior_sha" ]]; then
          LOCAL_EDITS+=("$path")
        fi
      fi
    done < <(manifest_files "$NEW_MANIFEST")

    NEW_ENV_KEYS=()
    while IFS=$'\t' read -r ep es; do
      cur="${COMPOSE_PROJECT_DIR}/${ep}"
      tmp_ex="$(mktemp)"
      if curl -fsSL "${RAW_BASE}/${es}" -o "$tmp_ex"; then
        while IFS= read -r k; do
          NEW_ENV_KEYS+=("${ep}:${k}")
        done < <(env_missing_keys "$cur" "$tmp_ex")
      fi
      rm -f "$tmp_ex"
    done < <(manifest_env_schemas "$NEW_MANIFEST")

    if (( ${#CHANGED_FILES[@]} > 0 || ${#NEW_ENV_KEYS[@]} > 0 )); then
      HOST_PHASE_RAN=1
      write_state sub_phase host_files

      # Snapshot
      if ! BACKUP_DIR="$(snapshot_create "$COMPOSE_PROJECT_DIR" "$OLD_VERSION" "$CUR_MANIFEST")"; then
        write_state status failed sub_phase null finished_at "$(now)" error_message "snapshot failed"
        exit 1
      fi
      write_state backup_path "$BACKUP_DIR"

      # Migrate legacy layout (idempotent)
      migrate_legacy_layout "$COMPOSE_PROJECT_DIR"

      # Apply file changes
      changed_paths_csv=""
      for row in "${CHANGED_FILES[@]}"; do
        IFS='|' read -r path src expected mode owner <<< "$row"
        if ! apply_managed_file "$COMPOSE_PROJECT_DIR" "$RAW_BASE" "$src" "$path" "$expected" "$mode" "$owner"; then
          echo "[helper] file apply failed: $path — restoring snapshot" >&2
          snapshot_restore "$COMPOSE_PROJECT_DIR" "$BACKUP_DIR" || true
          write_state status failed sub_phase null finished_at "$(now)" error_message "apply failed: $path"
          exit 1
        fi
        changed_paths_csv+="${changed_paths_csv:+,}${path}"
      done

      # Merge env files
      while IFS=$'\t' read -r ep es; do
        cur="${COMPOSE_PROJECT_DIR}/${ep}"
        tmp_ex="$(mktemp)"
        if curl -fsSL "${RAW_BASE}/${es}" -o "$tmp_ex"; then
          if ! merge_env_file "$cur" "$tmp_ex"; then
            rm -f "$tmp_ex"
            snapshot_restore "$COMPOSE_PROJECT_DIR" "$BACKUP_DIR" || true
            write_state status failed sub_phase null finished_at "$(now)" error_message "env merge failed: $ep"
            exit 1
          fi
        fi
        rm -f "$tmp_ex"
      done < <(manifest_env_schemas "$NEW_MANIFEST")

      # Install new manifest
      cp -a "$NEW_MANIFEST" "$CUR_MANIFEST"

      # Record state
      local_edits_csv="$(IFS=,; echo "${LOCAL_EDITS[*]:-}")"
      write_state host_files_changed "$changed_paths_csv" \
                  local_edits_overwritten "$local_edits_csv"

      snapshot_prune "$COMPOSE_PROJECT_DIR" 3
    fi
  fi

  # ── Phase C: image swap (existing flow) ─────────────────────────────────────
  write_state sub_phase image_swap
  rewrite_env "$NEW_API_IMAGE" "$NEW_WEB_IMAGE"
  docker compose down --timeout 30
  docker compose up -d

  if wait_for_healthy "$API_CONTAINER" "$HEALTH_TIMEOUT_SECONDS" \
     && wait_for_healthy "$WEB_CONTAINER" "$HEALTH_TIMEOUT_SECONDS"; then
    write_state status idle sub_phase null finished_at "$(now)" error_message null
    echo "[helper] update succeeded"
    exit 0
  fi

  # ── Phase D: rollback ───────────────────────────────────────────────────────
  echo "[helper] new version unhealthy — rolling back"
  write_state error_message "health check timeout"
  if (( HOST_PHASE_RAN == 1 )) && [[ -n "$BACKUP_DIR" ]]; then
    snapshot_restore "$COMPOSE_PROJECT_DIR" "$BACKUP_DIR" || true
  fi
  rewrite_env "$OLD_API_IMAGE" "$OLD_WEB_IMAGE"
  docker compose down --timeout 30
  docker compose up -d

  if wait_for_healthy "$API_CONTAINER" "$HEALTH_TIMEOUT_SECONDS" \
     && wait_for_healthy "$WEB_CONTAINER" "$HEALTH_TIMEOUT_SECONDS"; then
    write_state status rolled_back sub_phase null finished_at "$(now)" error_message "new version failed health check"
    echo "[helper] rolled back successfully"
    exit 0
  fi

  write_state status failed sub_phase null finished_at "$(now)" error_message "rollback also failed - manual intervention required"
  echo "[helper] catastrophic failure"
  exit 1
fi
