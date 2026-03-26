#!/usr/bin/env bash
# upgrade-selfhosted.sh — Upgrade HyperTrader self-hosted to the latest version
# Usage: ./scripts/upgrade-selfhosted.sh [--env-file PATH] [--skip-backup]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_FILE=".env.selfhosted"
COMPOSE_FILE="docker-compose.selfhosted.yml"
SKIP_BACKUP=false

# ─── Colours ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── Argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --env-file)     shift; ENV_FILE="$1" ;;
    --skip-backup)  SKIP_BACKUP=true ;;
    -h|--help)
      echo "Usage: $0 [--env-file PATH] [--skip-backup]"
      echo
      echo "  --env-file     Path to the env file (default: .env.selfhosted)"
      echo "  --skip-backup  Skip the pre-upgrade backup (not recommended)"
      exit 0
      ;;
    *) error "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# ─── Pre-flight checks ────────────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  error "Environment file not found: $ENV_FILE"
  error "Have you run install-selfhosted.sh first?"
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  error "Compose file not found: $COMPOSE_FILE"
  exit 1
fi

# ─── Pre-upgrade backup ───────────────────────────────────────────────────────
if [[ "$SKIP_BACKUP" == "false" ]]; then
  info "Running pre-upgrade backup..."
  "$SCRIPT_DIR/backup-selfhosted.sh" --env-file "$ENV_FILE" --quiet
  success "Backup complete"
else
  warn "Skipping pre-upgrade backup (--skip-backup)"
fi

# ─── Pull latest code (if in git repo) ───────────────────────────────────────
if [[ -d ".git" ]]; then
  info "Pulling latest changes from git..."
  git pull --ff-only || warn "git pull failed — continuing with local files"
fi

# ─── Rebuild and restart ──────────────────────────────────────────────────────
info "Rebuilding images..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --pull

info "Restarting stack with new images..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

# ─── Smoke test ───────────────────────────────────────────────────────────────
info "Waiting for services to be healthy..."
PORT_VALUE=$(grep -E '^PUBLIC_PORT=' "$ENV_FILE" | cut -d= -f2 || echo "80")
PORT_VALUE="${PORT_VALUE:-80}"
BASE_URL="http://localhost:${PORT_VALUE}"

MAX_RETRIES=20
RETRY_DELAY=3
n=0
until curl -sf "${BASE_URL}/health" -o /dev/null 2>/dev/null; do
  n=$((n+1))
  if [[ $n -ge $MAX_RETRIES ]]; then
    error "API did not become healthy after upgrade"
    echo
    error "Check container logs:"
    echo "  docker compose --env-file $ENV_FILE -f $COMPOSE_FILE logs"
    exit 1
  fi
  info "Still waiting... ($n/$MAX_RETRIES)"
  sleep "$RETRY_DELAY"
done

# ─── Show running versions ────────────────────────────────────────────────────
info "Running containers:"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo
success "Upgrade complete! Stack is healthy at ${BASE_URL}"
