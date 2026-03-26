#!/usr/bin/env bash
# install-selfhosted.sh — First-time install for HyperTrader self-hosted
# Usage: ./scripts/install-selfhosted.sh [--port PORT] [--env-file PATH]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_SOURCE="deploy/.env.selfhosted.example"
ENV_FILE=".env.selfhosted"
COMPOSE_FILE="docker-compose.selfhosted.yml"

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
    --port)     shift; PORT="$1" ;;
    --env-file) shift; ENV_FILE="$1" ;;
    -h|--help)
      echo "Usage: $0 [--port PORT] [--env-file PATH]"
      echo
      echo "  --port       Override PUBLIC_PORT in the env file"
      echo "  --env-file   Path to the env file (default: .env.selfhosted)"
      exit 0
      ;;
    *) error "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# ─── Pre-flight checks ────────────────────────────────────────────────────────
info "Checking prerequisites..."

if ! command -v docker &>/dev/null; then
  error "Docker is not installed. Install Docker first: https://docs.docker.com/engine/install/"
  exit 1
fi

if ! docker compose version &>/dev/null; then
  error "Docker Compose plugin not found. Install it: https://docs.docker.com/compose/install/"
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  error "Compose file not found: $COMPOSE_FILE"
  error "Run this script from the project root directory."
  exit 1
fi

success "Prerequisites OK"

# ─── Environment file ─────────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  warn "Environment file already exists: $ENV_FILE"
  warn "Skipping copy — using existing file. Delete it to start fresh."
else
  if [[ ! -f "$ENV_SOURCE" ]]; then
    error "Example env file not found: $ENV_SOURCE"
    exit 1
  fi
  cp "$ENV_SOURCE" "$ENV_FILE"
  success "Created $ENV_FILE from $ENV_SOURCE"
  echo
  warn "⚠  IMPORTANT: Edit $ENV_FILE before continuing."
  warn "   At minimum, set:"
  warn "     SECRET_KEY      — run: openssl rand -hex 32"
  warn "     ADMIN_PASSWORD  — choose a strong password"
  warn "     ADMIN_EMAIL     — your admin email"
  warn "     DOCKER_GID      — run: getent group docker | cut -d: -f3"
  echo
  read -r -p "Have you edited $ENV_FILE? [y/N] " ans
  if [[ "${ans,,}" != "y" ]]; then
    info "Open $ENV_FILE, fill in the required values, then re-run this script."
    exit 0
  fi
fi

# Apply optional port override
if [[ -n "${PORT:-}" ]]; then
  if [[ ! "$PORT" =~ ^[0-9]{1,5}$ ]] || [[ "$PORT" -gt 65535 ]]; then
    error "--port must be a numeric port (1-65535)"; exit 1
  fi
  info "Overriding PUBLIC_PORT=$PORT"
  if command -v sed &>/dev/null; then
    sed -i "s/^PUBLIC_PORT=.*/PUBLIC_PORT=$PORT/" "$ENV_FILE"
  fi
fi

# ─── Create data directory ────────────────────────────────────────────────────
if [[ ! -d "data" ]]; then
  mkdir -p data
  success "Created data/ directory"
fi

# ─── Build and start ──────────────────────────────────────────────────────────
info "Building images and starting stack..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

# ─── Smoke test ───────────────────────────────────────────────────────────────
info "Waiting for services to be healthy..."
PORT_VALUE=$(grep -E '^PUBLIC_PORT=' "$ENV_FILE" | cut -d= -f2 | tr -d '"[:space:]' || echo "80")
PORT_VALUE="${PORT_VALUE:-80}"
BASE_URL="http://localhost:${PORT_VALUE}"

MAX_RETRIES=20
RETRY_DELAY=3
n=0
until curl -sf "${BASE_URL}/health" -o /dev/null 2>/dev/null; do
  n=$((n+1))
  if [[ $n -ge $MAX_RETRIES ]]; then
    error "API did not become healthy after $((MAX_RETRIES * RETRY_DELAY))s"
    echo
    error "Check container logs:"
    echo "  docker compose --env-file $ENV_FILE -f $COMPOSE_FILE logs"
    exit 1
  fi
  info "Still waiting... ($n/$MAX_RETRIES)"
  sleep "$RETRY_DELAY"
done

success "Stack is up and healthy!"
echo
info "Dashboard: ${BASE_URL}"
info "Health:    ${BASE_URL}/health"
info "Setup:     ${BASE_URL}/api/v1/auth/setup-status"
echo
success "Installation complete. Open ${BASE_URL} in your browser to complete setup."
