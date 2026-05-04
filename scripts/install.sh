#!/usr/bin/env bash
# =============================================================================
# HyperTrader Manager — VPS Install Script
# =============================================================================
# Usage:
#   Latest release:
#     curl -sSL https://raw.githubusercontent.com/andreinasui/hyper-trader-manager/main/scripts/install.sh | sudo bash
#
#   Specific version:
#     curl -sSL https://raw.githubusercontent.com/andreinasui/hyper-trader-manager/refs/tags/v0.1.1/scripts/install.sh | sudo bash
#
# Requirements:
#   - Running as root
#   - Docker installed and daemon running
#   - docker compose plugin OR docker-compose standalone
#   - curl available
# =============================================================================
set -euo pipefail

# ── Version (set at release time; empty = fetch latest tag from GitHub API) ───
PINNED_VERSION=""

# ── Constants ─────────────────────────────────────────────────────────────────
REPO_OWNER="andreinasui"
REPO_NAME="hyper-trader-manager"
INSTALL_DIR="/opt/hyper-trader"
MANAGER_BIN="/usr/local/bin/hyper-trader-manager"
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

info() { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die() {
  error "$*"
  exit 1
}
header() { echo -e "\n${BOLD}${BLUE}==> $*${RESET}"; }

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

# docker compose (plugin or standalone) must be available
if docker compose version &>/dev/null 2>&1; then
  success "Compose: docker compose (plugin)"
elif command -v docker-compose &>/dev/null; then
  success "Compose: docker-compose (standalone)"
else
  die "Neither 'docker compose' plugin nor 'docker-compose' standalone was found. Install Docker Compose: https://docs.docker.com/compose/install/"
fi

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

# ── Phase 2: Resolve release version ─────────────────────────────────────────
header "Resolving release version"

if [[ -n "${PINNED_VERSION}" ]]; then
  RELEASE_TAG="${PINNED_VERSION}" # e.g. v0.2.0  — used as git ref
  IMAGE_TAG="${PINNED_VERSION#v}" # e.g.  0.2.0  — used as image tag
  success "Using pinned version: ${RELEASE_TAG} (image tag: ${IMAGE_TAG})"
else
  TAGS_JSON=$(curl -sf "${GITHUB_API}/tags" 2>/dev/null || true)

  if [[ -n "${TAGS_JSON}" ]] && echo "${TAGS_JSON}" | grep -q '"name"'; then
    RAW_TAG=$(echo "${TAGS_JSON}" | grep '"name"' | head -1 | sed 's/.*"name": *"\([^"]*\)".*/\1/')
    RELEASE_TAG="${RAW_TAG}" # e.g. v0.2.0  — used as git ref
    IMAGE_TAG="${RAW_TAG#v}" # e.g.  0.2.0  — used as image tag
    success "Latest tag: ${RELEASE_TAG} (image tag: ${IMAGE_TAG})"
  else
    error "No tags found. Cannot determine a version tag — aborting."
    exit 1
  fi
fi

# ── Phase 3: Create directory structure ──────────────────────────────────────
header "Creating install directory"

mkdir -p "${INSTALL_DIR}/traefik/dynamic"
touch "${INSTALL_DIR}/traefik/acme.json"
chmod 600 "${INSTALL_DIR}/traefik/acme.json"

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

download "${RAW_BASE}/environments/prod/docker-compose.yml" "${INSTALL_DIR}/docker-compose.yml"
download "${RAW_BASE}/environments/prod/.env.example" "${INSTALL_DIR}/.env.example"
download "${RAW_BASE}/environments/prod/api.env.example" "${INSTALL_DIR}/api.env.example"
download "${RAW_BASE}/environments/prod/traefik/traefik.template.yml" "${INSTALL_DIR}/traefik/traefik.yml"
download "${RAW_BASE}/environments/prod/traefik/dynamic/00-bootstrap.yml" "${INSTALL_DIR}/traefik/dynamic/00-bootstrap.yml"
download "${RAW_BASE}/scripts/hyper-trader-manager.sh" "${MANAGER_BIN}"

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

# --- .env ---
cp "${INSTALL_DIR}/.env.example" "${INSTALL_DIR}/.env"

sed -i "s|^DOCKER_GID=.*|DOCKER_GID=${DOCKER_GID}|" "${INSTALL_DIR}/.env"
sed -i "s|^DOCKER_SOCK=.*|DOCKER_SOCK=${DOCKER_SOCK}|" "${INSTALL_DIR}/.env"
sed -i "s|^HYPERTRADER_API_IMAGE=.*|HYPERTRADER_API_IMAGE=${GHCR_PREFIX}/${REPO_NAME}-api:${IMAGE_TAG}|" "${INSTALL_DIR}/.env"
sed -i "s|^HYPERTRADER_WEB_IMAGE=.*|HYPERTRADER_WEB_IMAGE=${GHCR_PREFIX}/${REPO_NAME}-web:${IMAGE_TAG}|" "${INSTALL_DIR}/.env"
sed -i "s|^COMPOSE_PROJECT_DIR=.*|COMPOSE_PROJECT_DIR=${INSTALL_DIR}|" "${INSTALL_DIR}/.env"
sed -i "s|^HELPER_IMAGE=.*|HELPER_IMAGE=${GHCR_PREFIX}/${REPO_NAME}-update-helper:${IMAGE_TAG}|" "${INSTALL_DIR}/.env"

success "Created ${INSTALL_DIR}/.env"

# --- api.env ---
cp "${INSTALL_DIR}/api.env.example" "${INSTALL_DIR}/api.env"

success "Created ${INSTALL_DIR}/api.env"

# Fix ownership: entire install directory belongs to the invoking user, not root
chown -R "${REAL_USER}:${REAL_GROUP}" "${INSTALL_DIR}"
success "Ownership set to ${REAL_USER}:${REAL_GROUP}"

# The API container runs as UID 1000 (hypertrader) and needs to write Traefik
# config files into traefik/. Ensure that directory is owned by UID 1000
# regardless of who invoked the install script (e.g. root on a root-only VPS).
chown -R 1000:1000 "${INSTALL_DIR}/traefik"
success "Traefik config directory ownership set to 1000:1000 (API container user)"

# ── Phase 7: Install management script ───────────────────────────────────────
header "Installing management script"

chmod +x "${MANAGER_BIN}"
success "Installed: ${MANAGER_BIN}"

# ── Phase 8: Summary ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}  HyperTrader Manager — Install Complete${RESET}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Install directory:${RESET} ${INSTALL_DIR}"
echo -e "  ${BOLD}Release:${RESET}           ${RELEASE_TAG}"
echo -e "  ${BOLD}API image:${RESET}         ${GHCR_PREFIX}/${REPO_NAME}-api:${IMAGE_TAG}"
echo -e "  ${BOLD}Web image:${RESET}         ${GHCR_PREFIX}/${REPO_NAME}-web:${IMAGE_TAG}"
echo ""
echo -e "${YELLOW}${BOLD}  !! Post-install configuration required:${RESET}"
echo ""
echo -e "  Edit ${BOLD}${INSTALL_DIR}/api.env${RESET}"
echo -e "    -> Set ${BOLD}CORS_ORIGINS${RESET} to your domain or VPS IP"
echo -e "       e.g.  CORS_ORIGINS=https://yourdomain.com"
echo ""
echo -e "  Edit ${BOLD}${INSTALL_DIR}/.env${RESET} if you need non-standard ports"
echo -e "    -> PUBLIC_PORT (default: 80)"
echo -e "    -> HTTPS_PUBLIC_PORT (default: 443)"
echo ""
echo -e "  After editing, start the service:"
echo -e "    ${BOLD}hyper-trader-manager start${RESET}"
echo ""
echo -e "  Management commands:"
echo -e "    ${BOLD}hyper-trader-manager start${RESET}    — pull images and start"
echo -e "    ${BOLD}hyper-trader-manager stop${RESET}     — stop all containers"
echo -e "    ${BOLD}hyper-trader-manager restart${RESET}  — stop then start"
echo -e "    ${BOLD}hyper-trader-manager status${RESET}   — show container status"
echo -e "    ${BOLD}hyper-trader-manager logs${RESET}     — follow logs"
echo -e "    ${BOLD}hyper-trader-manager update${RESET}   — pull new images and restart"
echo ""
