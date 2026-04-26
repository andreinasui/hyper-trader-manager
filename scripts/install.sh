#!/usr/bin/env bash
# =============================================================================
# HyperTrader Manager — VPS Install Script
# =============================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/andreinasui/hyper-trader-manager/main/scripts/install.sh | sudo bash
#
# Requirements:
#   - Running as root
#   - Docker installed and daemon running
#   - docker compose plugin OR docker-compose standalone
#   - curl available
# =============================================================================
set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────
REPO_OWNER="andreinasui"
REPO_NAME="hyper-trader-manager"
INSTALL_DIR="/opt/hyper-trader"
SERVICE_NAME="hyper-trader"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
GHCR_PREFIX="ghcr.io/${REPO_OWNER}"
GITHUB_API="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"
GITHUB_RAW="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }
header()  { echo -e "\n${BOLD}${BLUE}==> $*${RESET}"; }

# ── Phase 1: Prerequisites ────────────────────────────────────────────────────
header "Checking prerequisites"

# Must run as root
[[ "${EUID}" -eq 0 ]] || die "This script must be run as root. Use: sudo bash install.sh"

# curl must be available
command -v curl &>/dev/null || die "curl is required but not installed."

# Docker must be installed
command -v docker &>/dev/null || die "Docker is not installed. Install Docker first: https://docs.docker.com/engine/install/"

# Docker daemon must be running
docker info &>/dev/null || die "Docker daemon is not running. Start it with: systemctl start docker"

# Detect compose command (plugin preferred, standalone fallback)
if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    COMPOSE_BIN="/usr/bin/docker"
    COMPOSE_ARGS="compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
    COMPOSE_BIN="$(command -v docker-compose)"
    COMPOSE_ARGS=""
else
    die "Neither 'docker compose' plugin nor 'docker-compose' standalone was found. Install Docker Compose: https://docs.docker.com/compose/install/"
fi
success "Compose command: ${COMPOSE_CMD}"

# Detect the real user who invoked sudo (for ownership of install directory)
if [[ -n "${SUDO_USER:-}" ]]; then
    REAL_USER="${SUDO_USER}"
    REAL_GROUP=$(id -gn "${SUDO_USER}")
else
    REAL_USER="root"
    REAL_GROUP="root"
    warn "Not invoked via sudo — install directory will be owned by root."
fi
success "Install directory will be owned by: ${REAL_USER}:${REAL_GROUP}"

# Already-installed guard
if [[ -d "${INSTALL_DIR}" ]]; then
    warn "Already installed at ${INSTALL_DIR}. To reinstall, remove that directory first."
    exit 0
fi

# ── Phase 2: Detect latest release tag ───────────────────────────────────────
header "Fetching latest release version"

RELEASE_JSON=$(curl -sf "${GITHUB_API}/releases/latest" 2>/dev/null || true)

if [[ -n "${RELEASE_JSON}" ]] && echo "${RELEASE_JSON}" | grep -q '"tag_name"'; then
    RAW_TAG=$(echo "${RELEASE_JSON}" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')
    RELEASE_TAG="${RAW_TAG}"               # e.g. v0.2.0  — used as git ref
    IMAGE_TAG="${RAW_TAG#v}"               # e.g.  0.2.0  — used as image tag
    success "Latest release: ${RELEASE_TAG} (image tag: ${IMAGE_TAG})"
else
    warn "No releases found — downloading files from 'main' branch and using 'latest' image tag."
    RELEASE_TAG="main"
    IMAGE_TAG="latest"
fi

# ── Phase 3: Create directory structure ──────────────────────────────────────
header "Creating install directory"

mkdir -p "${INSTALL_DIR}/deploy/data/traefik/certs"
touch "${INSTALL_DIR}/deploy/data/traefik/acme.json"
chmod 600 "${INSTALL_DIR}/deploy/data/traefik/acme.json"

success "Created ${INSTALL_DIR}"

# ── Phase 4: Download files from release tag ──────────────────────────────────
header "Downloading application files (ref: ${RELEASE_TAG})"

RAW_BASE="${GITHUB_RAW}/${RELEASE_TAG}"

download() {
    local url="$1"
    local dest="$2"
    info "  ${url}"
    if ! curl -fsSL "${url}" -o "${dest}"; then
        die "Failed to download: ${url}"
    fi
}

download "${RAW_BASE}/deploy/docker-compose.prod.yml" "${INSTALL_DIR}/deploy/docker-compose.prod.yml"
download "${RAW_BASE}/deploy/.env.example"            "${INSTALL_DIR}/deploy/.env.example"
download "${RAW_BASE}/api/.env.example"               "${INSTALL_DIR}/deploy/api.env.example"

success "Files downloaded."

# ── Phase 5: Detect Docker socket and GID ────────────────────────────────────
header "Detecting Docker socket and GID"

if [[ -S "/var/run/docker.sock" ]]; then
    DOCKER_SOCK="/var/run/docker.sock"
elif [[ -S "/run/docker.sock" ]]; then
    DOCKER_SOCK="/run/docker.sock"
else
    die "Docker socket not found at /var/run/docker.sock or /run/docker.sock. Is Docker running?"
fi

DOCKER_GID=$(stat -c '%g' "${DOCKER_SOCK}")

success "Docker socket: ${DOCKER_SOCK}"
success "Docker GID:    ${DOCKER_GID}"

# ── Phase 6: Create env files ─────────────────────────────────────────────────
header "Generating environment files"

DEPLOY_DIR="${INSTALL_DIR}/deploy"

# --- deploy/.env ---
cp "${DEPLOY_DIR}/.env.example" "${DEPLOY_DIR}/.env"

sed -i "s|^DOCKER_GID=.*|DOCKER_GID=${DOCKER_GID}|"         "${DEPLOY_DIR}/.env"
sed -i "s|^DOCKER_SOCK=.*|DOCKER_SOCK=${DOCKER_SOCK}|"       "${DEPLOY_DIR}/.env"
sed -i "s|^HYPERTRADER_API_IMAGE=.*|HYPERTRADER_API_IMAGE=${GHCR_PREFIX}/hypertrader-api:${IMAGE_TAG}|" "${DEPLOY_DIR}/.env"
sed -i "s|^HYPERTRADER_WEB_IMAGE=.*|HYPERTRADER_WEB_IMAGE=${GHCR_PREFIX}/hypertrader-web:${IMAGE_TAG}|" "${DEPLOY_DIR}/.env"

success "Created ${DEPLOY_DIR}/.env"

# --- deploy/api.env ---
cp "${DEPLOY_DIR}/api.env.example" "${DEPLOY_DIR}/api.env"

success "Created ${DEPLOY_DIR}/api.env"

# Fix ownership: entire install directory belongs to the invoking user, not root
chown -R "${REAL_USER}:${REAL_GROUP}" "${INSTALL_DIR}"
success "Ownership set to ${REAL_USER}:${REAL_GROUP}"

# ── Phase 7: Create systemd service ──────────────────────────────────────────
header "Creating systemd service"

# Build ExecStart / ExecStop lines based on detected compose command
if [[ "${COMPOSE_CMD}" == "docker compose" ]]; then
    EXEC_START="${COMPOSE_BIN} ${COMPOSE_ARGS} -f ${DEPLOY_DIR}/docker-compose.prod.yml up -d --pull always"
    EXEC_STOP="${COMPOSE_BIN} ${COMPOSE_ARGS} -f ${DEPLOY_DIR}/docker-compose.prod.yml down"
else
    EXEC_START="${COMPOSE_BIN} -f ${DEPLOY_DIR}/docker-compose.prod.yml up -d --pull always"
    EXEC_STOP="${COMPOSE_BIN} -f ${DEPLOY_DIR}/docker-compose.prod.yml down"
fi

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=HyperTrader Manager
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${DEPLOY_DIR}
ExecStart=${EXEC_START}
ExecStop=${EXEC_STOP}
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

success "Created ${SERVICE_FILE}"

# ── Phase 8: Enable and start ─────────────────────────────────────────────────
header "Enabling and starting service"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

if systemctl start "${SERVICE_NAME}"; then
    success "Service started."
else
    warn "Service failed to start. This may be expected if images are not yet available in the registry."
    warn "Check logs with: journalctl -u ${SERVICE_NAME} -n 50"
fi

# ── Phase 9: Summary ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}  HyperTrader Manager — Install Complete${RESET}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Install directory:${RESET} ${INSTALL_DIR}"
echo -e "  ${BOLD}Release:${RESET}           ${RELEASE_TAG}"
echo -e "  ${BOLD}API image:${RESET}         ${GHCR_PREFIX}/hypertrader-api:${IMAGE_TAG}"
echo -e "  ${BOLD}Web image:${RESET}         ${GHCR_PREFIX}/hypertrader-web:${IMAGE_TAG}"
echo ""
echo -e "  ${BOLD}Service status:${RESET}"
systemctl status "${SERVICE_NAME}" --no-pager --lines=5 2>/dev/null || true
echo ""
echo -e "${YELLOW}${BOLD}  !! Post-install configuration required:${RESET}"
echo ""
echo -e "  Edit ${BOLD}${DEPLOY_DIR}/api.env${RESET}"
echo -e "    -> Set ${BOLD}CORS_ORIGINS${RESET} to your domain or VPS IP"
echo -e "       e.g.  CORS_ORIGINS=https://yourdomain.com"
echo ""
echo -e "  Edit ${BOLD}${DEPLOY_DIR}/.env${RESET} if you need non-standard ports"
echo -e "    -> PUBLIC_PORT (default: 80)"
echo -e "    -> HTTPS_PUBLIC_PORT (default: 443)"
echo ""
echo -e "  After editing, restart the service:"
echo -e "    ${BOLD}systemctl restart ${SERVICE_NAME}${RESET}"
echo ""
