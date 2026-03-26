#!/usr/bin/env bash
# backup.sh — Backup HyperTrader Manager data
# Usage: ./scripts/backup.sh [--env-file PATH] [--output-dir DIR] [--quiet]
#
# Creates a timestamped archive containing:
#   - data/db.sqlite        (SQLite database)
#   - data/traders/         (trader configuration files)
#   - .env                  (environment config, secrets redacted)
#
# The archive is written to BACKUP_DIR (default: ./backups)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_FILE=".env"
BACKUP_DIR="backups"
COMPOSE_FILE="docker-compose.yml"
QUIET=false

# ─── Colours ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { [[ "$QUIET" == "false" ]] && echo -e "${BLUE}[INFO]${NC}  $*" || true; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── Argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --env-file)    shift; ENV_FILE="$1" ;;
    --output-dir)  shift; BACKUP_DIR="$1" ;;
    --quiet)       QUIET=true ;;
    -h|--help)
      echo "Usage: $0 [--env-file PATH] [--output-dir DIR] [--quiet]"
      echo
      echo "  --env-file    Path to the env file (default: .env)"
      echo "  --output-dir  Directory where backups are written (default: backups/)"
      echo "  --quiet       Suppress informational output"
      exit 0
      ;;
    *) error "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# ─── Validate ────────────────────────────────────────────────────────────────
if [[ ! -d "data" ]]; then
  warn "data/ directory not found — nothing to back up."
  exit 0
fi

# ─── Prepare backup destination ──────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_NAME="hypertrader-backup-${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
STAGING_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

info "Preparing backup staging area..."

# ─── Copy data directory ──────────────────────────────────────────────────────
# NOTE: SQLite is copied while the API may still be running. For low-traffic
# instances this is generally safe, but for guaranteed consistency stop the
# stack first: docker compose down
cp -r data "$STAGING_DIR/data"
info "Included: data/"

# ─── Copy env file (redact secret values) ─────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  # Copy with secrets replaced by placeholder
  sed -E 's/^(SECRET_KEY|ADMIN_PASSWORD)=.*/\1=<REDACTED>/' "$ENV_FILE" \
    > "$STAGING_DIR/env.backup"
  info "Included: env config (secrets redacted)"
fi

# ─── Create archive ───────────────────────────────────────────────────────────
info "Creating archive: $BACKUP_PATH"
tar -czf "$BACKUP_PATH" -C "$STAGING_DIR" .

BACKUP_SIZE="$(du -sh "$BACKUP_PATH" | cut -f1)"

# ─── Rotate old backups (keep last 10) ────────────────────────────────────────
BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/hypertrader-backup-*.tar.gz 2>/dev/null | wc -l)
if [[ $BACKUP_COUNT -gt 10 ]]; then
  info "Rotating old backups (keeping last 10)..."
  ls -1t "${BACKUP_DIR}"/hypertrader-backup-*.tar.gz | tail -n +11 | xargs rm -f
fi

# ─── Done ────────────────────────────────────────────────────────────────────
success "Backup saved: $BACKUP_PATH ($BACKUP_SIZE)"
info "To restore, extract the archive:"
info "  tar -xzf $BACKUP_PATH -C /path/to/restore"
