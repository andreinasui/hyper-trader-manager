#!/usr/bin/env bash
# install.sh — First-time install for HyperTrader Manager
# Usage: ./scripts/install.sh [--port PORT]
#
# This script:
#   1. Checks prerequisites (Docker, Docker Compose)
#   2. Creates .env from template
#   3. Sets up initial Traefik config (HTTP mode)
#   4. Builds and starts the Docker stack
#   5. Waits for services to be healthy
#
# After installation, open the dashboard to:
#   - Create your admin account
#   - Configure SSL (Let's Encrypt or self-signed)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_SOURCE="deploy/.env.example"
ENV_FILE="deploy/.env"
COMPOSE_FILE="docker-compose.yml"

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
    -h|--help)
      echo "Usage: $0 [--port PORT]"
      echo
      echo "  --port       Override PUBLIC_PORT (default: 80)"
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

  # Generate ENCRYPTION_KEY if not already set
  if grep -q "ENCRYPTION_KEY=change-me" "$ENV_FILE"; then
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || openssl rand -base64 32)
    sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|" "$ENV_FILE"
    success "Generated ENCRYPTION_KEY automatically"
  fi

  # Detect and set DOCKER_GID
  if command -v getent &>/dev/null; then
    DETECTED_GID=$(getent group docker | cut -d: -f3 || echo "")
    if [[ -n "$DETECTED_GID" ]]; then
      sed -i "s/^DOCKER_GID=.*/DOCKER_GID=$DETECTED_GID/" "$ENV_FILE"
      success "Detected DOCKER_GID=$DETECTED_GID"
    fi
  fi

  echo
  info "Environment file created: $ENV_FILE"
  info "Review settings if needed (ENCRYPTION_KEY and DOCKER_GID auto-configured)"
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

# ─── Create data directories ─────────────────────────────────────────────────
info "Setting up data directories..."

mkdir -p data/traefik/certs
success "Created data/traefik/ structure"

# ─── Initial Traefik config (HTTP mode) ───────────────────────────────────────
# This is the minimal HTTP-only config for first boot.
# The SSL setup wizard will reconfigure Traefik for HTTPS.
if [[ ! -f "data/traefik/traefik.yml" ]]; then
  cat > data/traefik/traefik.yml << 'EOF'
# Initial HTTP-only config — SSL setup wizard will reconfigure this
entryPoints:
  web:
    address: ":80"

providers:
  file:
    filename: /etc/traefik/dynamic.yml
    watch: true
EOF
  success "Created initial Traefik static config"
fi

if [[ ! -f "data/traefik/dynamic.yml" ]]; then
  cat > data/traefik/dynamic.yml << 'EOF'
# Initial routing config — SSL setup wizard will update this
http:
  routers:
    health:
      rule: "Path(`/health`)"
      service: api
      entryPoints: [web]
      priority: 20
    api:
      rule: "PathPrefix(`/api`)"
      service: api
      entryPoints: [web]
      priority: 10
    web:
      rule: "PathPrefix(`/`)"
      service: web
      entryPoints: [web]
      priority: 1
  services:
    api:
      loadBalancer:
        servers:
          - url: "http://api:8000"
        healthCheck:
          path: /health
          interval: 10s
          timeout: 5s
    web:
      loadBalancer:
        servers:
          - url: "http://web:80"
EOF
  success "Created initial Traefik dynamic config"
fi

# ─── Build and start ──────────────────────────────────────────────────────────
info "Building images and starting stack..."
docker compose up -d --build

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
    echo "  docker compose logs"
    exit 1
  fi
  info "Still waiting... ($n/$MAX_RETRIES)"
  sleep "$RETRY_DELAY"
done

success "Stack is up and healthy!"
echo
echo "════════════════════════════════════════════════════════════════════"
info "Dashboard:     ${BASE_URL}"
info "Health check:  ${BASE_URL}/health"
echo "════════════════════════════════════════════════════════════════════"
echo
success "Installation complete!"
echo
info "Next steps:"
echo "  1. Open ${BASE_URL} in your browser"
echo "  2. Create your admin account (first-time setup)"
echo "  3. Configure SSL (Let's Encrypt or self-signed certificate)"
echo
info "After SSL setup, your dashboard will be available over HTTPS."
echo
info "Useful commands:"
echo "  docker compose logs -f          # View logs"
echo "  docker compose restart          # Restart services"
echo "  docker compose down             # Stop services"
