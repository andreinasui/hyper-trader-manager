# Environments Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `deploy/` and `data/` into a per-environment `environments/{dev,dev-ssl,prod}/` layout where each environment is fully self-contained with its own compose file, env templates, and Traefik data directory.

**Architecture:** Three environment directories (`dev`, `dev-ssl`, `prod`) each contain `docker-compose.yml`, `.env.example`, `api.env.example`, `traefik/` (config + data), `.gitignore`, and environment-specific extras (`pebble/`, `sqlitedb/`). `install.sh` downloads from `environments/prod/` and places files flat under `/opt/hyper-trader/`. The management script loses `DEPLOY_DIR` and points directly at `INSTALL_DIR/docker-compose.yml`.

**Tech Stack:** Docker Compose v2, bash scripts, YAML

---

## File Map

### Created
- `environments/dev/docker-compose.yml`
- `environments/dev/.env.example`
- `environments/dev/api.env.example`
- `environments/dev/.gitignore`
- `environments/dev/traefik/traefik.template.yml`
- `environments/dev/traefik/.gitignore`
- `environments/dev/traefik/dynamic/00-bootstrap.yml`
- `environments/dev/sqlitedb/.gitkeep`
- `environments/dev/sqlitedb/.gitignore`
- `environments/dev-ssl/docker-compose.yml`
- `environments/dev-ssl/.env.example`
- `environments/dev-ssl/api.env.example`
- `environments/dev-ssl/api-pebble.env.example`
- `environments/dev-ssl/.gitignore`
- `environments/dev-ssl/pebble/pebble-config.json`
- `environments/dev-ssl/pebble/pebble.minica.pem`
- `environments/dev-ssl/traefik/traefik.template.yml`
- `environments/dev-ssl/traefik/.gitignore`
- `environments/dev-ssl/traefik/dynamic/00-bootstrap.yml`
- `environments/dev-ssl/traefik/dynamic/10-tls.yml`
- `environments/dev-ssl/sqlitedb/.gitkeep`
- `environments/dev-ssl/sqlitedb/.gitignore`
- `environments/prod/docker-compose.yml`
- `environments/prod/.env.example`
- `environments/prod/api.env.example`
- `environments/prod/.gitignore`
- `environments/prod/traefik/traefik.template.yml`
- `environments/prod/traefik/.gitignore`
- `environments/prod/traefik/dynamic/00-bootstrap.yml`

### Modified
- `scripts/install.sh` — remove `DEPLOY_DIR`, update download paths + dest paths + chown
- `scripts/hyper-trader-manager.sh` — remove `DEPLOY_DIR`, point `COMPOSE_FILE` to `INSTALL_DIR/docker-compose.yml`
- `DEV_SETUP.md` — update dev Docker stack commands, SSL file locations table, project structure tree
- `docs/SSL_LOCAL_TESTING.md` — update all paths for new dev-ssl layout; remove manual `acme.json` touch step (replaced by `traefik-acme-init`); remove overlay alternative (pebble compose deleted)
- `docs/QUICKSTART.md` — update manual install paths and data persistence table

### Deleted (via git rm)
- `deploy/` (all tracked files)
- `data/` (all tracked files)

---

## Task 1: Create git worktree

- [ ] **Step 1: Create the worktree from main**

```bash
git worktree add .worktrees/environments-restructure -b feature/environments-restructure
```

Expected output:
```
Preparing worktree (new branch 'feature/environments-restructure')
HEAD is now at 38b94b3 ...
```

- [ ] **Step 2: Verify worktree is on main's HEAD**

```bash
git -C .worktrees/environments-restructure log --oneline -1
```

Expected: the same commit hash as main (`38b94b3` or similar).

All subsequent steps run with working directory `.worktrees/environments-restructure` unless stated otherwise.

---

## Task 2: Create `environments/dev/`

**Files:** Create all listed under `environments/dev/`

- [ ] **Step 1: Create directory structure**

Run from `.worktrees/environments-restructure`:

```bash
mkdir -p environments/dev/traefik/dynamic
mkdir -p environments/dev/sqlitedb
```

- [ ] **Step 2: Create `environments/dev/docker-compose.yml`**

```yaml
# HyperTrader Manager Stack — local development
#
# Usage (from repo root):
#   One-time setup:
#     cp environments/dev/.env.example environments/dev/.env
#     cp environments/dev/api.env.example environments/dev/api.env
#     cp environments/dev/traefik/traefik.template.yml environments/dev/traefik/traefik.yml
#     touch environments/dev/traefik/acme.json && chmod 600 environments/dev/traefik/acme.json
#
#   Start the stack:
#     docker compose -f environments/dev/docker-compose.yml \
#       --env-file environments/dev/.env up -d --build

services:
  # ============================================
  # Traefik reverse proxy
  # Routes /api/* → api, /* → web
  # ============================================
  traefik:
    image: traefik:v3.3
    container_name: hypertrader-traefik
    restart: unless-stopped
    ports:
      - "${PUBLIC_PORT:-80}:80"
      - "${HTTPS_PUBLIC_PORT:-443}:443"
    volumes:
      - ./traefik:/etc/traefik:ro
      - ./traefik/acme.json:/letsencrypt/acme.json
    networks:
      - hypertrader
    healthcheck:
      test: ["CMD", "traefik", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

  # ============================================
  # API service (FastAPI + uvicorn)
  # ============================================
  api:
    build:
      context: ../../api
      dockerfile: Dockerfile
    container_name: hypertrader-api
    restart: unless-stopped
    env_file:
      - api.env
    group_add:
      - ${DOCKER_GID}
    volumes:
      # Persistent data: SQLite database and trader configs
      - ./sqlitedb/:/app/data
      # Docker socket access for managing trader containers
      - ${DOCKER_SOCK}:/var/run/docker.sock
      # Bind mount for Traefik config (wizard writes here)
      - ./traefik:/host-traefik
    networks:
      - hypertrader
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # ============================================
  # Web service
  # ============================================
  web:
    build:
      context: ../../web
      dockerfile: Dockerfile
    container_name: hypertrader-web
    restart: unless-stopped
    environment:
      - NODE_ENV=development
    networks:
      - hypertrader
    healthcheck:
      test:
        [
          "CMD",
          "wget",
          "--no-verbose",
          "--tries=1",
          "--spider",
          "http://localhost:3000/",
        ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    depends_on:
      api:
        condition: service_healthy

networks:
  hypertrader:
    driver: bridge
```

- [ ] **Step 3: Create `environments/dev/.env.example`**

```bash
# ============================================
# HyperTrader Manager - Dev Configuration
# ============================================
# Shared variables used by docker-compose for the dev stack.
# Copy to .env and configure for your environment
#
# Usage:
#   cp environments/dev/.env.example environments/dev/.env
#   cp environments/dev/api.env.example environments/dev/api.env
#   docker compose -f environments/dev/docker-compose.yml \
#     --env-file environments/dev/.env up -d --build

# ============================================
# Docker Configuration
# ============================================
# Docker socket group ID (find with: stat -c '%g' /var/run/docker.sock)
# Common values: 999 (Debian/Ubuntu), 993 (Fedora/RHEL)
DOCKER_GID=999

# Docker socket path
DOCKER_SOCK=/var/run/docker.sock

# ============================================
# Network Configuration
# ============================================
# Port to expose publicly (HTTP)
PUBLIC_PORT=80

# Port to expose publicly (HTTPS)
HTTPS_PUBLIC_PORT=443
```

- [ ] **Step 4: Create `environments/dev/api.env.example`**

```bash
# ============================================
# HyperTrader API - Development Configuration
# ============================================
# Environment variables for the FastAPI backend service (local Docker dev stack)
# Copy to api.env:
#   cp environments/dev/api.env.example environments/dev/api.env

# ============================================
# Environment
# ============================================
ENVIRONMENT=development

# ============================================
# Database
# ============================================
# SQLite database path (absolute path inside container)
DATABASE_URL=sqlite:////app/data/hypertrader.db

# ============================================
# Self-Hosted Configuration
# ============================================
# Base directory for app data (Traefik config, SSL certs, trader configs)
# This is the path inside the container
DATA_DIR=/app/data

# ============================================
# Logging
# ============================================
# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=DEBUG
```

- [ ] **Step 5: Create `environments/dev/.gitignore`**

```
.env
api.env
```

- [ ] **Step 6: Create `environments/dev/traefik/traefik.template.yml`**

```yaml
# Bootstrap template for Traefik static config.
# This file is the committed source of truth.
#
# Usage (one-time, before running the dev docker compose stack):
#   cp environments/dev/traefik/traefik.template.yml environments/dev/traefik/traefik.yml
#
# traefik.yml is gitignored — the SSL wizard overwrites it with domain/ACME config.
# Never edit traefik.yml directly; update this template instead.
entryPoints:
  web:
    address: :80
  websecure:
    address: :443
ping: {}
providers:
  file:
    directory: /etc/traefik/dynamic
    watch: true
```

- [ ] **Step 7: Create `environments/dev/traefik/.gitignore`**

```
# Runtime-written files — overwritten by the API and Traefik at startup.
# Only the template and seed config belong in version control.
traefik.yml
acme.json
certs/
dynamic/*
!dynamic/00-bootstrap.yml
```

- [ ] **Step 8: Create `environments/dev/traefik/dynamic/00-bootstrap.yml`**

(Same content as `data/traefik/dynamic/00-bootstrap.yml`.)

```yaml
# Initial Traefik dynamic config - HTTP only.
# Routes /api/* to the API container, everything else to the web container.
# Overwritten by the SSL setup wizard once a domain certificate is provisioned.
http:
  routers:
    health:
      rule: "Path(`/health`)"
      service: web
      entryPoints:
        - web
      priority: 20
    api:
      rule: "PathPrefix(`/api`)"
      service: api
      entryPoints:
        - web
      priority: 10
    web:
      rule: "PathPrefix(`/`)"
      service: web
      entryPoints:
        - web
      priority: 1

  services:
    api:
      loadBalancer:
        servers:
          - url: "http://api:8000"
        healthCheck:
          path: /health
          interval: "10s"
          timeout: "5s"
    web:
      loadBalancer:
        servers:
          - url: "http://web:3000"
        healthCheck:
          path: /
          interval: "10s"
          timeout: "5s"
```

- [ ] **Step 9: Create `environments/dev/sqlitedb/.gitkeep`** (empty file)

- [ ] **Step 10: Create `environments/dev/sqlitedb/.gitignore`**

```
*.db
```

- [ ] **Step 11: Validate compose file syntax**

Run from `.worktrees/environments-restructure` (with a temp setup so docker compose can parse it):

```bash
docker compose -f environments/dev/docker-compose.yml config --quiet
```

Expected: exits 0 with no errors. (It may warn about missing `.env` / `api.env` — those are runtime files, not errors.)

- [ ] **Step 12: Commit**

```bash
git -C .worktrees/environments-restructure add environments/dev/
git -C .worktrees/environments-restructure commit -m "feat: add environments/dev/ - self-contained local dev stack"
```

---

## Task 3: Create `environments/dev-ssl/`

**Files:** Create all listed under `environments/dev-ssl/`

This environment also carries the `traefik-acme-init` busybox service (from the `feature/ssl-wizard-restart-ux` branch) which ensures `acme.json` is a file with mode `600` before Traefik starts. This replaces the manual `touch acme.json && chmod 600` one-time setup step.

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p environments/dev-ssl/traefik/dynamic
mkdir -p environments/dev-ssl/sqlitedb
mkdir -p environments/dev-ssl/pebble
```

- [ ] **Step 2: Create `environments/dev-ssl/docker-compose.yml`**

```yaml
# HyperTrader Manager Stack — dev with local SSL (Pebble)
#
# Self-contained compose file for testing the SSL wizard end-to-end locally.
# Uses Pebble (Let's Encrypt's test ACME server) instead of real Let's Encrypt.
#
# Usage (from repo root):
#   One-time setup:
#     cp environments/dev-ssl/.env.example environments/dev-ssl/.env
#     cp environments/dev-ssl/api.env.example environments/dev-ssl/api.env
#     cp environments/dev-ssl/api-pebble.env.example environments/dev-ssl/api-pebble.env
#     cp environments/dev-ssl/traefik/traefik.template.yml environments/dev-ssl/traefik/traefik.yml
#
#   Start the stack:
#     docker compose -f environments/dev-ssl/docker-compose.yml \
#       --env-file environments/dev-ssl/.env up -d --build
#
#   Browse to http://hypertrader.localtest.me/
#   Submit the SSL wizard with domain=hypertrader.localtest.me
#   Browser ends up on https://hypertrader.localtest.me (cert from Pebble —
#   browser will warn; trust it once for testing)
#
# To return to vanilla dev: use environments/dev/docker-compose.yml instead.

services:
  # ============================================
  # Init: ensure acme.json exists with mode 600 before Traefik starts.
  # Traefik refuses to use the file if permissions are too open (>600).
  # If Docker created acme.json as a directory (happens when the file didn't
  # exist on the host at first stack-up), remove it before creating the file.
  # ============================================
  traefik-acme-init:
    image: busybox
    command: sh -c "[ -d /data/acme.json ] && rm -rf /data/acme.json; touch /data/acme.json && chmod 600 /data/acme.json"
    volumes:
      - ./traefik:/data

  # ============================================
  # Traefik reverse proxy
  # Routes /api/* → api, /* → web
  # Also answers to hypertrader.localtest.me on the internal docker network so
  # Pebble's HTTP-01 challenge resolves to traefik (port 80) rather than leaving
  # the network. LEGO_CA_CERTIFICATES makes Traefik's ACME client trust Pebble's
  # MiniCA cert.
  # ============================================
  traefik:
    image: traefik:v3.3
    container_name: hypertrader-traefik
    restart: unless-stopped
    ports:
      - "${PUBLIC_PORT:-80}:80"
      - "${HTTPS_PUBLIC_PORT:-443}:443"
    environment:
      - LEGO_CA_CERTIFICATES=/etc/ssl/pebble.minica.pem
    volumes:
      - ./traefik:/etc/traefik:ro
      - ./traefik/acme.json:/letsencrypt/acme.json
      - ./pebble/pebble.minica.pem:/etc/ssl/pebble.minica.pem:ro
    networks:
      hypertrader:
        aliases:
          - hypertrader.localtest.me
    healthcheck:
      test: ["CMD", "traefik", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s
    depends_on:
      traefik-acme-init:
        condition: service_completed_successfully

  # ============================================
  # API service (FastAPI + uvicorn)
  # ============================================
  api:
    build:
      context: ../../api
      dockerfile: Dockerfile
    container_name: hypertrader-api
    restart: unless-stopped
    env_file:
      - api.env
      - api-pebble.env
    group_add:
      - ${DOCKER_GID}
    volumes:
      # Persistent data: SQLite database and trader configs
      - ./sqlitedb/:/app/data
      # Docker socket access for managing trader containers
      - ${DOCKER_SOCK}:/var/run/docker.sock
      # Bind mount for Traefik config (wizard writes here — isolated from dev/traefik/)
      - ./traefik:/host-traefik
    networks:
      - hypertrader
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    depends_on:
      pebble:
        condition: service_started

  # ============================================
  # Web service
  # ============================================
  web:
    build:
      context: ../../web
      dockerfile: Dockerfile
    container_name: hypertrader-web
    restart: unless-stopped
    environment:
      - NODE_ENV=development
    networks:
      - hypertrader
    healthcheck:
      test:
        [
          "CMD",
          "wget",
          "--no-verbose",
          "--tries=1",
          "--spider",
          "http://localhost:3000/",
        ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    depends_on:
      api:
        condition: service_healthy

  # ============================================
  # Pebble — Let's Encrypt's test ACME server
  # Listens on :14000 (ACME directory) and :15000 (management) inside the
  # hypertrader docker network.
  # ============================================
  pebble:
    image: ghcr.io/letsencrypt/pebble:latest
    container_name: hypertrader-pebble
    restart: unless-stopped
    command:
      - "-config"
      - "/test/config/pebble-config.json"
    environment:
      - PEBBLE_VA_NOSLEEP=1
      - PEBBLE_VA_ALWAYS_VALID=0
    volumes:
      - ./pebble/pebble-config.json:/test/config/pebble-config.json:ro
    networks:
      - hypertrader

networks:
  hypertrader:
    driver: bridge
```

- [ ] **Step 3: Create `environments/dev-ssl/.env.example`**

Same content as `environments/dev/.env.example` except update the Usage comment:

```bash
# ============================================
# HyperTrader Manager - Dev-SSL Configuration
# ============================================
# Shared variables used by docker-compose for the dev-ssl stack.
# Copy to .env and configure for your environment
#
# Usage:
#   cp environments/dev-ssl/.env.example environments/dev-ssl/.env
#   cp environments/dev-ssl/api.env.example environments/dev-ssl/api.env
#   cp environments/dev-ssl/api-pebble.env.example environments/dev-ssl/api-pebble.env
#   docker compose -f environments/dev-ssl/docker-compose.yml \
#     --env-file environments/dev-ssl/.env up -d --build

# ============================================
# Docker Configuration
# ============================================
# Docker socket group ID (find with: stat -c '%g' /var/run/docker.sock)
# Common values: 999 (Debian/Ubuntu), 993 (Fedora/RHEL)
DOCKER_GID=999

# Docker socket path
DOCKER_SOCK=/var/run/docker.sock

# ============================================
# Network Configuration
# ============================================
# Port to expose publicly (HTTP)
PUBLIC_PORT=80

# Port to expose publicly (HTTPS)
HTTPS_PUBLIC_PORT=443
```

- [ ] **Step 4: Create `environments/dev-ssl/api.env.example`**

Same content as `environments/dev/api.env.example` (the base config loaded before pebble overrides):

```bash
# ============================================
# HyperTrader API - Dev-SSL Base Configuration
# ============================================
# Base API environment variables for the dev-ssl stack.
# Loaded before api-pebble.env; values here can be overridden by api-pebble.env.
#
# Copy to api.env:
#   cp environments/dev-ssl/api.env.example environments/dev-ssl/api.env

ENVIRONMENT=development

DATABASE_URL=sqlite:////app/data/hypertrader.db

DATA_DIR=/app/data

LOG_LEVEL=DEBUG
```

- [ ] **Step 5: Create `environments/dev-ssl/api-pebble.env.example`**

```bash
# ============================================
# HyperTrader API - Pebble SSL Overrides
# ============================================
# Overrides for the SSL wizard e2e test with Pebble.
# Loaded on top of api.env — only set values that differ from the base config.
#
# Copy to api-pebble.env:
#   cp environments/dev-ssl/api-pebble.env.example environments/dev-ssl/api-pebble.env

# Force production code paths so the SSL wizard is reachable.
ENVIRONMENT=production

# Point Traefik's ACME resolver at Pebble instead of Let's Encrypt.
ACME_CA_SERVER=https://pebble:14000/dir

DATABASE_URL=sqlite:////app/data/hypertrader-pebble.db
DATA_DIR=/app/data
LOG_LEVEL=DEBUG
```

- [ ] **Step 6: Create `environments/dev-ssl/.gitignore`**

```
.env
api.env
api-pebble.env
```

- [ ] **Step 7: Copy pebble files from `deploy/pebble/`**

```bash
cp deploy/pebble/pebble-config.json environments/dev-ssl/pebble/pebble-config.json
cp deploy/pebble/pebble.minica.pem environments/dev-ssl/pebble/pebble.minica.pem
```

- [ ] **Step 8: Create `environments/dev-ssl/traefik/traefik.template.yml`**

```yaml
# Bootstrap template for Traefik static config.
# This file is the committed source of truth.
#
# Usage (one-time, before running the dev-ssl docker compose stack):
#   cp environments/dev-ssl/traefik/traefik.template.yml environments/dev-ssl/traefik/traefik.yml
#
# traefik.yml is gitignored — the SSL wizard overwrites it with domain/ACME config.
# Never edit traefik.yml directly; update this template instead.
entryPoints:
  web:
    address: :80
  websecure:
    address: :443
ping: {}
providers:
  file:
    directory: /etc/traefik/dynamic
    watch: true
```

- [ ] **Step 9: Create `environments/dev-ssl/traefik/.gitignore`**

```
# Runtime-written files — overwritten by the API and Traefik at startup.
# Only the template and seed configs belong in version control.
traefik.yml
acme.json
certs/
dynamic/*
!dynamic/00-bootstrap.yml
!dynamic/10-tls.yml
```

- [ ] **Step 10: Create `environments/dev-ssl/traefik/dynamic/00-bootstrap.yml`**

Identical content to `environments/dev/traefik/dynamic/00-bootstrap.yml`:

```yaml
# Initial Traefik dynamic config - HTTP only.
# Routes /api/* to the API container, everything else to the web container.
# Overwritten by the SSL setup wizard once a domain certificate is provisioned.
http:
  routers:
    health:
      rule: "Path(`/health`)"
      service: web
      entryPoints:
        - web
      priority: 20
    api:
      rule: "PathPrefix(`/api`)"
      service: api
      entryPoints:
        - web
      priority: 10
    web:
      rule: "PathPrefix(`/`)"
      service: web
      entryPoints:
        - web
      priority: 1

  services:
    api:
      loadBalancer:
        servers:
          - url: "http://api:8000"
        healthCheck:
          path: /health
          interval: "10s"
          timeout: "5s"
    web:
      loadBalancer:
        servers:
          - url: "http://web:3000"
        healthCheck:
          path: /
          interval: "10s"
          timeout: "5s"
```

- [ ] **Step 11: Create `environments/dev-ssl/traefik/dynamic/10-tls.yml`**

```yaml
http:
  routers:
    health-tls:
      rule: Host(`hypertrader.localtest.me`) && Path(`/health`)
      service: api
      entryPoints:
      - websecure
      priority: 20
      tls:
        certResolver: letsencrypt
    api-tls:
      rule: Host(`hypertrader.localtest.me`) && PathPrefix(`/api`)
      service: api
      entryPoints:
      - websecure
      priority: 10
      tls:
        certResolver: letsencrypt
    web-tls:
      rule: Host(`hypertrader.localtest.me`)
      service: web
      entryPoints:
      - websecure
      priority: 1
      tls:
        certResolver: letsencrypt
```

- [ ] **Step 12: Create `environments/dev-ssl/sqlitedb/.gitkeep`** (empty file)

- [ ] **Step 13: Create `environments/dev-ssl/sqlitedb/.gitignore`**

```
*.db
```

- [ ] **Step 14: Validate compose file syntax**

```bash
docker compose -f environments/dev-ssl/docker-compose.yml config --quiet
```

Expected: exits 0 with no errors.

- [ ] **Step 15: Commit**

```bash
git -C .worktrees/environments-restructure add environments/dev-ssl/
git -C .worktrees/environments-restructure commit -m "feat: add environments/dev-ssl/ - Pebble SSL testing stack"
```

---

## Task 4: Create `environments/prod/`

**Files:** Create all listed under `environments/prod/`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p environments/prod/traefik/dynamic
```

- [ ] **Step 2: Create `environments/prod/docker-compose.yml`**

```yaml
# HyperTrader Manager Stack — production
#   Installed by scripts/install.sh to /opt/hyper-trader/docker-compose.yml
#   docker compose -f docker-compose.yml up -d

services:
  # ============================================
  # Traefik reverse proxy
  # Routes /api/* → api, /* → web
  # ============================================
  traefik:
    image: traefik:v3.3
    container_name: hypertrader-traefik
    restart: unless-stopped
    ports:
      - "${PUBLIC_PORT:-80}:80"
      - "${HTTPS_PUBLIC_PORT:-443}:443"
    volumes:
      - ./traefik:/etc/traefik:ro
      - ./traefik/acme.json:/letsencrypt/acme.json
    networks:
      - hypertrader
    healthcheck:
      test: ["CMD", "traefik", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

  # ============================================
  # API service (FastAPI + uvicorn)
  # ============================================
  api:
    image: ${HYPERTRADER_API_IMAGE}
    container_name: hypertrader-api
    restart: unless-stopped
    env_file:
      - api.env
    group_add:
      - ${DOCKER_GID:-999}
    volumes:
      # Persistent data: SQLite database and trader configs
      - hypertrader-data:/app/data
      # Docker socket access for managing trader containers
      - ${DOCKER_SOCK}:/var/run/docker.sock
      # Bind mount for Traefik config (wizard writes here)
      - ./traefik:/host-traefik
    networks:
      - hypertrader
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # ============================================
  # Web service
  # ============================================
  web:
    image: ${HYPERTRADER_WEB_IMAGE}
    container_name: hypertrader-web
    restart: unless-stopped
    environment:
      - NODE_ENV=production
    networks:
      - hypertrader
    healthcheck:
      test:
        [
          "CMD",
          "wget",
          "--no-verbose",
          "--tries=1",
          "--spider",
          "http://localhost:3000/",
        ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    depends_on:
      api:
        condition: service_healthy

networks:
  hypertrader:
    driver: bridge

volumes:
  hypertrader-data:
```

- [ ] **Step 3: Create `environments/prod/.env.example`**

```bash
# ============================================
# HyperTrader Manager - Production Configuration
# ============================================
# Shared variables used by docker-compose for all services
# Installed to /opt/hyper-trader/.env by scripts/install.sh
#
# Usage (Production):
#   cp .env.example .env
#   cp api.env.example api.env
#   # Edit files with your production values
#   docker compose -f docker-compose.yml up -d

# ============================================
# Docker Configuration
# ============================================
# Docker socket group ID (find with: stat -c '%g' /var/run/docker.sock)
# Common values: 999 (Debian/Ubuntu), 993 (Fedora/RHEL)
DOCKER_GID=999

# Docker socket path
DOCKER_SOCK=/var/run/docker.sock

# ============================================
# Network Configuration
# ============================================
# Port to expose publicly (HTTP)
PUBLIC_PORT=80

# Port to expose publicly (HTTPS)
HTTPS_PUBLIC_PORT=443

# ============================================
# Container Images
# ============================================
# Full image URLs (registry/name:tag) for each service.
# Set automatically by the install script using the latest GitHub release tag.
HYPERTRADER_API_IMAGE=ghcr.io/andreinasui/hyper-trader-manager-api:0.1.0
HYPERTRADER_WEB_IMAGE=ghcr.io/andreinasui/hyper-trader-manager-web:0.1.0
```

- [ ] **Step 4: Create `environments/prod/api.env.example`**

Same content as `api/.env.example` (production config; this is what install.sh downloads as `api.env.example`):

```bash
# ============================================
# HyperTrader API - Production Configuration
# ============================================
# Environment variables for the FastAPI backend service
# Installed to /opt/hyper-trader/api.env.example by scripts/install.sh
# Copy to api.env and configure:
#   cp api.env.example api.env

# ============================================
# Environment
# ============================================
ENVIRONMENT=production

# ============================================
# Database
# ============================================
# SQLite database path (absolute path inside container)
DATABASE_URL=sqlite:////app/data/hypertrader.db

# ============================================
# Self-Hosted Configuration
# ============================================
# Base directory for app data (Traefik config, SSL certs)
# This is the path inside the container
DATA_DIR=/app/data

# ============================================
# Logging
# ============================================
# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

- [ ] **Step 5: Create `environments/prod/.gitignore`**

```
.env
api.env
```

- [ ] **Step 6: Create `environments/prod/traefik/traefik.template.yml`**

```yaml
# Bootstrap template for Traefik static config.
# This file is the committed source of truth.
#
# install.sh downloads this file as traefik/traefik.yml on the VPS.
# traefik.yml is gitignored — the SSL wizard overwrites it with domain/ACME config.
# Never edit traefik.yml directly; update this template instead.
entryPoints:
  web:
    address: :80
  websecure:
    address: :443
ping: {}
providers:
  file:
    directory: /etc/traefik/dynamic
    watch: true
```

- [ ] **Step 7: Create `environments/prod/traefik/.gitignore`**

```
# Runtime-written files — overwritten by the API and Traefik at startup.
# Only the template and seed config belong in version control.
traefik.yml
acme.json
certs/
dynamic/*
!dynamic/00-bootstrap.yml
```

- [ ] **Step 8: Create `environments/prod/traefik/dynamic/00-bootstrap.yml`**

Identical content to `environments/dev/traefik/dynamic/00-bootstrap.yml`:

```yaml
# Initial Traefik dynamic config - HTTP only.
# Routes /api/* to the API container, everything else to the web container.
# Overwritten by the SSL setup wizard once a domain certificate is provisioned.
http:
  routers:
    health:
      rule: "Path(`/health`)"
      service: web
      entryPoints:
        - web
      priority: 20
    api:
      rule: "PathPrefix(`/api`)"
      service: api
      entryPoints:
        - web
      priority: 10
    web:
      rule: "PathPrefix(`/`)"
      service: web
      entryPoints:
        - web
      priority: 1

  services:
    api:
      loadBalancer:
        servers:
          - url: "http://api:8000"
        healthCheck:
          path: /health
          interval: "10s"
          timeout: "5s"
    web:
      loadBalancer:
        servers:
          - url: "http://web:3000"
        healthCheck:
          path: /
          interval: "10s"
          timeout: "5s"
```

- [ ] **Step 9: Validate compose file syntax**

```bash
docker compose -f environments/prod/docker-compose.yml config --quiet
```

Expected: exits 0 with no errors.

- [ ] **Step 10: Commit**

```bash
git -C .worktrees/environments-restructure add environments/prod/
git -C .worktrees/environments-restructure commit -m "feat: add environments/prod/ - production stack config"
```

---

## Task 5: Update `scripts/install.sh`

**File:** `scripts/install.sh`

The script currently creates `${INSTALL_DIR}/deploy/data/traefik/` and downloads files into `${INSTALL_DIR}/deploy/`. After this task everything goes flat under `${INSTALL_DIR}/`.

Key changes:
- Phase 3: `mkdir -p ${INSTALL_DIR}/deploy/data/traefik/dynamic` → `${INSTALL_DIR}/traefik/dynamic`
- Phase 4: download destinations and source paths updated
- Phase 6: remove `DEPLOY_DIR` variable; replace all `${DEPLOY_DIR}` with `${INSTALL_DIR}`
- Phase 6: final chown path updated
- Phase 8 summary: update file references

- [ ] **Step 1: Update Phase 3 (directory creation)**

Find:
```bash
mkdir -p "${INSTALL_DIR}/deploy/data/traefik/dynamic"
touch "${INSTALL_DIR}/deploy/data/traefik/acme.json"
chmod 600 "${INSTALL_DIR}/deploy/data/traefik/acme.json"
```

Replace with:
```bash
mkdir -p "${INSTALL_DIR}/traefik/dynamic"
touch "${INSTALL_DIR}/traefik/acme.json"
chmod 600 "${INSTALL_DIR}/traefik/acme.json"
```

- [ ] **Step 2: Update Phase 4 (download calls)**

Find:
```bash
download "${RAW_BASE}/deploy/docker-compose.prod.yml" "${INSTALL_DIR}/deploy/docker-compose.prod.yml"
download "${RAW_BASE}/deploy/.env.example" "${INSTALL_DIR}/deploy/.env.example"
download "${RAW_BASE}/api/.env.example" "${INSTALL_DIR}/deploy/api.env.example"
download "${RAW_BASE}/data/traefik/traefik.template.yml" "${INSTALL_DIR}/deploy/data/traefik/traefik.yml"
download "${RAW_BASE}/data/traefik/dynamic/00-bootstrap.yml" "${INSTALL_DIR}/deploy/data/traefik/dynamic/00-bootstrap.yml"
```

Replace with:
```bash
download "${RAW_BASE}/environments/prod/docker-compose.yml" "${INSTALL_DIR}/docker-compose.yml"
download "${RAW_BASE}/environments/prod/.env.example" "${INSTALL_DIR}/.env.example"
download "${RAW_BASE}/environments/prod/api.env.example" "${INSTALL_DIR}/api.env.example"
download "${RAW_BASE}/environments/prod/traefik/traefik.template.yml" "${INSTALL_DIR}/traefik/traefik.yml"
download "${RAW_BASE}/environments/prod/traefik/dynamic/00-bootstrap.yml" "${INSTALL_DIR}/traefik/dynamic/00-bootstrap.yml"
```

- [ ] **Step 3: Update Phase 6 (env file generation)**

Find the entire Phase 6 block:
```bash
DEPLOY_DIR="${INSTALL_DIR}/deploy"

# --- deploy/.env ---
cp "${DEPLOY_DIR}/.env.example" "${DEPLOY_DIR}/.env"

sed -i "s|^DOCKER_GID=.*|DOCKER_GID=${DOCKER_GID}|" "${DEPLOY_DIR}/.env"
sed -i "s|^DOCKER_SOCK=.*|DOCKER_SOCK=${DOCKER_SOCK}|" "${DEPLOY_DIR}/.env"
sed -i "s|^HYPERTRADER_API_IMAGE=.*|HYPERTRADER_API_IMAGE=${GHCR_PREFIX}/${REPO_NAME}-api:${IMAGE_TAG}|" "${DEPLOY_DIR}/.env"
sed -i "s|^HYPERTRADER_WEB_IMAGE=.*|HYPERTRADER_WEB_IMAGE=${GHCR_PREFIX}/${REPO_NAME}-web:${IMAGE_TAG}|" "${DEPLOY_DIR}/.env"

success "Created ${DEPLOY_DIR}/.env"

# --- deploy/api.env ---
cp "${DEPLOY_DIR}/api.env.example" "${DEPLOY_DIR}/api.env"

success "Created ${DEPLOY_DIR}/api.env"

# Fix ownership: entire install directory belongs to the invoking user, not root
chown -R "${REAL_USER}:${REAL_GROUP}" "${INSTALL_DIR}"
success "Ownership set to ${REAL_USER}:${REAL_GROUP}"

# The API container runs as UID 1000 (hypertrader) and needs to write Traefik
# config files into data/traefik. Ensure that directory is owned by UID 1000
# regardless of who invoked the install script (e.g. root on a root-only VPS).
chown -R 1000:1000 "${INSTALL_DIR}/deploy/data/traefik"
success "Traefik config directory ownership set to 1000:1000 (API container user)"
```

Replace with:
```bash
# --- .env ---
cp "${INSTALL_DIR}/.env.example" "${INSTALL_DIR}/.env"

sed -i "s|^DOCKER_GID=.*|DOCKER_GID=${DOCKER_GID}|" "${INSTALL_DIR}/.env"
sed -i "s|^DOCKER_SOCK=.*|DOCKER_SOCK=${DOCKER_SOCK}|" "${INSTALL_DIR}/.env"
sed -i "s|^HYPERTRADER_API_IMAGE=.*|HYPERTRADER_API_IMAGE=${GHCR_PREFIX}/${REPO_NAME}-api:${IMAGE_TAG}|" "${INSTALL_DIR}/.env"
sed -i "s|^HYPERTRADER_WEB_IMAGE=.*|HYPERTRADER_WEB_IMAGE=${GHCR_PREFIX}/${REPO_NAME}-web:${IMAGE_TAG}|" "${INSTALL_DIR}/.env"

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
```

- [ ] **Step 4: Update Phase 8 (summary output)**

Find:
```bash
echo -e "  Edit ${BOLD}${DEPLOY_DIR}/api.env${RESET}"
echo -e "    -> Set ${BOLD}CORS_ORIGINS${RESET} to your domain or VPS IP"
echo -e "       e.g.  CORS_ORIGINS=https://yourdomain.com"
echo ""
echo -e "  Edit ${BOLD}${DEPLOY_DIR}/.env${RESET} if you need non-standard ports"
```

Replace with:
```bash
echo -e "  Edit ${BOLD}${INSTALL_DIR}/api.env${RESET}"
echo -e "    -> Set ${BOLD}CORS_ORIGINS${RESET} to your domain or VPS IP"
echo -e "       e.g.  CORS_ORIGINS=https://yourdomain.com"
echo ""
echo -e "  Edit ${BOLD}${INSTALL_DIR}/.env${RESET} if you need non-standard ports"
```

- [ ] **Step 5: Verify bash syntax**

```bash
bash -n scripts/install.sh
```

Expected: exits 0 with no output (no syntax errors).

- [ ] **Step 6: Commit**

```bash
git -C .worktrees/environments-restructure add scripts/install.sh
git -C .worktrees/environments-restructure commit -m "feat: update install.sh for environments/ layout"
```

---

## Task 6: Update `scripts/hyper-trader-manager.sh`

**File:** `scripts/hyper-trader-manager.sh`

Remove `DEPLOY_DIR` and update `COMPOSE_FILE`.

- [ ] **Step 1: Update the path constants**

Find:
```bash
INSTALL_DIR="/opt/hyper-trader"
DEPLOY_DIR="${INSTALL_DIR}/deploy"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.prod.yml"
```

Replace with:
```bash
INSTALL_DIR="/opt/hyper-trader"
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"
```

- [ ] **Step 2: Verify bash syntax**

```bash
bash -n scripts/hyper-trader-manager.sh
```

Expected: exits 0 with no output.

- [ ] **Step 3: Commit**

```bash
git -C .worktrees/environments-restructure add scripts/hyper-trader-manager.sh
git -C .worktrees/environments-restructure commit -m "feat: update hyper-trader-manager.sh for flat install layout"
```

---

## Task 7: Delete `deploy/` and `data/`

Remove all tracked files in the old directories.

- [ ] **Step 1: git rm both directories**

```bash
git -C .worktrees/environments-restructure rm -r deploy/ data/
```

Expected output lists all removed tracked files (untracked files like `.env`, `*.db` remain on disk — that's fine; they're local dev state).

- [ ] **Step 2: Verify the old paths are gone from the index**

```bash
git -C .worktrees/environments-restructure status
```

Expected: all `deploy/` and `data/` tracked files shown as `deleted`.

- [ ] **Step 3: Commit**

```bash
git -C .worktrees/environments-restructure commit -m "feat: remove deploy/ and data/ - replaced by environments/"
```

---

## Task 8: Update `DEV_SETUP.md`

**File:** `DEV_SETUP.md`

Three sections need updating.

- [ ] **Step 1: Update "SSL File Locations (Production)" table**

Find:
```markdown
| File / Directory | Purpose |
|-----------------|---------|
| `data/traefik/traefik.yml` | Main Traefik static config |
| `data/traefik/dynamic/` | Traefik dynamic routing config |
| `data/traefik/certs/` | Self-signed certificate files |
| `data/traefik/acme.json` | Let's Encrypt certificate store (mode 600) |
```

Replace with:
```markdown
| File / Directory | Purpose |
|-----------------|---------|
| `traefik/traefik.yml` | Main Traefik static config (on the VPS: `/opt/hyper-trader/traefik/traefik.yml`) |
| `traefik/dynamic/` | Traefik dynamic routing config |
| `traefik/certs/` | Self-signed certificate files |
| `traefik/acme.json` | Let's Encrypt certificate store (mode 600) |
```

- [ ] **Step 2: Update "Docker Compose Dev Stack" section**

Find:
```markdown
## Docker Compose Dev Stack

`deploy/docker-compose.dev.yml` runs the full stack locally in Docker (Traefik +
API + Web). This is separate from the standard `just api` / `just web` dev workflow;
use it when you need to test the containerised stack.

`data/traefik/traefik.yml` is gitignored — create it from the template before first
run:

```bash
# From repo root (one-time)
cp data/traefik/traefik.template.yml data/traefik/traefik.yml
touch data/traefik/acme.json && chmod 600 data/traefik/acme.json

# Start
docker compose -f deploy/docker-compose.dev.yml --env-file deploy/.env up -d --build
```

For local SSL testing with Pebble, see [docs/SSL_LOCAL_TESTING.md](docs/SSL_LOCAL_TESTING.md).
```

Replace with:
```markdown
## Docker Compose Dev Stack

`environments/dev/docker-compose.yml` runs the full stack locally in Docker (Traefik +
API + Web). This is separate from the standard `just api` / `just web` dev workflow;
use it when you need to test the containerised stack.

`environments/dev/traefik/traefik.yml` is gitignored — create it from the template before first
run:

```bash
# From repo root (one-time)
cp environments/dev/.env.example environments/dev/.env
cp environments/dev/api.env.example environments/dev/api.env
cp environments/dev/traefik/traefik.template.yml environments/dev/traefik/traefik.yml
touch environments/dev/traefik/acme.json && chmod 600 environments/dev/traefik/acme.json

# Start
docker compose -f environments/dev/docker-compose.yml --env-file environments/dev/.env up -d --build
```

For local SSL testing with Pebble, see [docs/SSL_LOCAL_TESTING.md](docs/SSL_LOCAL_TESTING.md).
```

- [ ] **Step 3: Update "Project Structure" section**

Find:
```markdown
├── deploy/                 # Production deployment configs
│   ├── traefik/            # Traefik routing config
│   └── .env.example        # Production env template
├── docker-compose.yml      # Production stack
├── justfile                # Root commands
└── DEV_SETUP.md           # This file
```

Replace with:
```markdown
├── environments/           # Per-environment Docker stacks
│   ├── dev/                # Local dev (Traefik + API + Web)
│   ├── dev-ssl/            # Local dev with Pebble SSL testing
│   └── prod/               # Production (downloaded by install.sh)
├── justfile                # Root commands
└── DEV_SETUP.md           # This file
```

- [ ] **Step 4: Commit**

```bash
git -C .worktrees/environments-restructure add DEV_SETUP.md
git -C .worktrees/environments-restructure commit -m "docs: update DEV_SETUP.md for environments/ layout"
```

---

## Task 9: Update `docs/SSL_LOCAL_TESTING.md`

**File:** `docs/SSL_LOCAL_TESTING.md`

Three sections need updating: Setup, Run the stack, and Reset. Also remove the overlay alternative (pebble compose deleted) and update the pebble cert path.

- [ ] **Step 1: Update "Setup (one-time)" section**

Find:
```markdown
```bash
cp deploy/.env.api.pebble.example deploy/.env.api.pebble
cp data/traefik/traefik.template.yml data/traefik-pebble/traefik.yml
touch data/traefik-pebble/acme.json && chmod 600 data/traefik-pebble/acme.json
```

`data/traefik-pebble/traefik.yml` and `acme.json` are gitignored — they're safe to
delete and recreate. `data/traefik/` is never touched by the Pebble stack.
```

Replace with:
```markdown
```bash
cp environments/dev-ssl/.env.example environments/dev-ssl/.env
cp environments/dev-ssl/api.env.example environments/dev-ssl/api.env
cp environments/dev-ssl/api-pebble.env.example environments/dev-ssl/api-pebble.env
cp environments/dev-ssl/traefik/traefik.template.yml environments/dev-ssl/traefik/traefik.yml
```

`environments/dev-ssl/traefik/traefik.yml` is gitignored — it's safe to delete and
recreate. `acme.json` is created automatically by the `traefik-acme-init` service on
first stack-up (no manual `touch` required). `environments/dev/` is never touched by
the dev-ssl stack.
```

- [ ] **Step 2: Update "Run the stack" section**

Find:
```markdown
Use the combined `docker-compose.dev_ssl.yml` file (merges `docker-compose.dev.yml` +
`docker-compose.pebble.yml` into a single file):

```bash
docker compose \
  -f deploy/docker-compose.dev_ssl.yml \
  --env-file deploy/.env \
  up -d --build
```

<details>
<summary>Alternative: two-file overlay approach</summary>

```bash
docker compose \
  -f deploy/docker-compose.dev.yml \
  -f deploy/docker-compose.pebble.yml \
  --env-file deploy/.env \
  up -d --build
```
</details>
```

Replace with:
```markdown
```bash
docker compose \
  -f environments/dev-ssl/docker-compose.yml \
  --env-file environments/dev-ssl/.env \
  up -d --build
```
```

- [ ] **Step 3: Update curl cacert path**

Find:
```markdown
If you want curl to validate the chain instead of `-k`, pass
`--cacert deploy/pebble/pebble.minica.pem`.
```

Replace with:
```markdown
If you want curl to validate the chain instead of `-k`, pass
`--cacert environments/dev-ssl/pebble/pebble.minica.pem`.
```

- [ ] **Step 4: Update the overlay explanation paragraph**

Find:
```markdown
Three things make the e2e work, all defined in `docker-compose.dev_ssl.yml`
```

Replace with:
```markdown
Three things make the e2e work, all defined in `environments/dev-ssl/docker-compose.yml`
```

- [ ] **Step 5: Update "Reset" section**

Find:
```markdown
```bash
docker compose -f deploy/docker-compose.dev_ssl.yml down -v

# Wipe Pebble runtime files
rm -f data/traefik-pebble/traefik.yml \
      data/traefik-pebble/acme.json \
      data/traefik-pebble/dynamic/10-tls.yml

# Re-initialise for the next run
cp data/traefik/traefik.template.yml data/traefik-pebble/traefik.yml
touch data/traefik-pebble/acme.json && chmod 600 data/traefik-pebble/acme.json
```

`data/traefik/` is never modified by the Pebble stack — no `git checkout` needed.
```

Replace with:
```markdown
```bash
docker compose -f environments/dev-ssl/docker-compose.yml down -v

# Wipe Pebble runtime files
rm -f environments/dev-ssl/traefik/traefik.yml \
      environments/dev-ssl/traefik/acme.json \
      environments/dev-ssl/traefik/dynamic/10-tls.yml

# Re-initialise for the next run
cp environments/dev-ssl/traefik/traefik.template.yml environments/dev-ssl/traefik/traefik.yml
# acme.json is re-created automatically by traefik-acme-init on next stack-up
```

`environments/dev/` is never modified by the dev-ssl stack.
```

- [ ] **Step 6: Commit**

```bash
git -C .worktrees/environments-restructure add docs/SSL_LOCAL_TESTING.md
git -C .worktrees/environments-restructure commit -m "docs: update SSL_LOCAL_TESTING.md for environments/ layout"
```

---

## Task 10: Update `docs/QUICKSTART.md`

**File:** `docs/QUICKSTART.md`

Two sections need updating: "Manual Installation" and "Data Persistence".

- [ ] **Step 1: Update "Manual Installation" section**

Find:
```markdown
```bash
# 1. Create environment file
cp deploy/.env.example deploy/.env

# 2. Edit deploy/.env — set ADMIN_PASSWORD, DOCKER_GID, and any other required values
#    (No encryption key needed — private keys are stored as Docker Swarm secrets)

# 3. Get your Docker group ID
getent group docker | cut -d: -f3
# Copy to DOCKER_GID in deploy/.env

# 4. Create Traefik config directories
mkdir -p data/traefik/certs

# 5. Create initial Traefik config
cat > data/traefik/traefik.yml << 'EOF'
entryPoints:
  web:
    address: ":80"
providers:
  file:
    filename: /etc/traefik/dynamic.yml
    watch: true
EOF

cat > data/traefik/dynamic.yml << 'EOF'
http:
  routers:
    api:
      rule: "PathPrefix(`/api`)"
      service: api
      entryPoints: [web]
    web:
      rule: "PathPrefix(`/`)"
      service: web
      entryPoints: [web]
  services:
    api:
      loadBalancer:
        servers:
          - url: "http://api:8000"
    web:
      loadBalancer:
        servers:
          - url: "http://web:80"
EOF

# 6. Start the stack
docker compose up -d --build

# 7. Check health
curl http://localhost/health
```
```

Replace with:
```markdown
```bash
# 1. Run the install script (handles all of the below automatically)
curl -sSL https://raw.githubusercontent.com/andreinasui/hyper-trader-manager/main/scripts/install.sh | sudo bash

# Or manually:

# 1. Create install directory and Traefik config directory
sudo mkdir -p /opt/hyper-trader/traefik/dynamic
sudo touch /opt/hyper-trader/traefik/acme.json
sudo chmod 600 /opt/hyper-trader/traefik/acme.json

# 2. Download production files
RAW="https://raw.githubusercontent.com/andreinasui/hyper-trader-manager/main"
sudo curl -fsSL "${RAW}/environments/prod/docker-compose.yml" -o /opt/hyper-trader/docker-compose.yml
sudo curl -fsSL "${RAW}/environments/prod/.env.example" -o /opt/hyper-trader/.env.example
sudo curl -fsSL "${RAW}/environments/prod/api.env.example" -o /opt/hyper-trader/api.env.example
sudo curl -fsSL "${RAW}/environments/prod/traefik/traefik.template.yml" -o /opt/hyper-trader/traefik/traefik.yml
sudo curl -fsSL "${RAW}/environments/prod/traefik/dynamic/00-bootstrap.yml" -o /opt/hyper-trader/traefik/dynamic/00-bootstrap.yml
sudo curl -fsSL "${RAW}/scripts/hyper-trader-manager.sh" -o /usr/local/bin/hyper-trader-manager
sudo chmod +x /usr/local/bin/hyper-trader-manager

# 3. Create env files
sudo cp /opt/hyper-trader/.env.example /opt/hyper-trader/.env
sudo cp /opt/hyper-trader/api.env.example /opt/hyper-trader/api.env
# Edit /opt/hyper-trader/.env and /opt/hyper-trader/api.env with your values

# 4. Set ownership (replace 'youruser' with the user that will manage the stack)
sudo chown -R youruser:youruser /opt/hyper-trader
sudo chown -R 1000:1000 /opt/hyper-trader/traefik

# 5. Start the stack
hyper-trader-manager start

# 6. Check health
curl http://localhost/health
```
```

- [ ] **Step 2: Update "Data Persistence" section**

Find:
```markdown
All data is stored in `./data/` on the host:

| Path | Contents |
|------|----------|
| `data/hypertrader.db` | SQLite database |
| `data/traders/` | Trader configuration files |
| `data/traefik/` | Traefik config and SSL certs |
| `data/traefik/acme.json` | Let's Encrypt certificates |
| `data/traefik/certs/` | Self-signed certificates |
```

Replace with:
```markdown
All data is stored under `/opt/hyper-trader/` on the VPS host:

| Path | Contents |
|------|----------|
| `hypertrader-data` (Docker named volume) | SQLite database and trader configs |
| `traefik/` | Traefik config and SSL certs |
| `traefik/traefik.yml` | Active Traefik static config |
| `traefik/dynamic/` | Traefik dynamic routing config |
| `traefik/acme.json` | Let's Encrypt certificates (mode 600) |
| `traefik/certs/` | Self-signed certificate files |
```

- [ ] **Step 3: Update "Environment Variables" key settings table** (optional, table caption)

Find:
```markdown
Key settings in `deploy/.env`:
```

Replace with:
```markdown
Key settings in `/opt/hyper-trader/.env`:
```

- [ ] **Step 4: Update "Reconfigure SSL" section**

Find:
```markdown
```bash
# Delete SSL config from database
sqlite3 data/hypertrader.db "DELETE FROM ssl_config;"

# Restart to trigger SSL wizard
docker compose restart
```
```

Replace with:
```markdown
```bash
# Delete SSL config from database (database is in the hypertrader-data Docker named volume)
docker exec hypertrader-api sqlite3 /app/data/hypertrader.db "DELETE FROM ssl_config;"

# Restart to trigger SSL wizard
hyper-trader-manager restart
```
```

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/environments-restructure add docs/QUICKSTART.md
git -C .worktrees/environments-restructure commit -m "docs: update QUICKSTART.md for environments/ layout"
```

---

## Task 11: Final verification

- [ ] **Step 1: Check git log for all task commits**

```bash
git -C .worktrees/environments-restructure log --oneline main..HEAD
```

Expected: 9 commits (Tasks 2–10, one each).

- [ ] **Step 2: Verify no old paths remain**

```bash
grep -r "deploy/" .worktrees/environments-restructure/scripts/ .worktrees/environments-restructure/DEV_SETUP.md .worktrees/environments-restructure/docs/ 2>/dev/null | grep -v ".git"
grep -r "data/traefik" .worktrees/environments-restructure/scripts/ .worktrees/environments-restructure/DEV_SETUP.md .worktrees/environments-restructure/docs/ 2>/dev/null | grep -v ".git"
```

Expected: no output.

- [ ] **Step 3: Validate all three compose files**

```bash
docker compose -f .worktrees/environments-restructure/environments/dev/docker-compose.yml config --quiet
docker compose -f .worktrees/environments-restructure/environments/dev-ssl/docker-compose.yml config --quiet
docker compose -f .worktrees/environments-restructure/environments/prod/docker-compose.yml config --quiet
```

Expected: all three exit 0.

- [ ] **Step 4: Verify bash scripts syntax**

```bash
bash -n .worktrees/environments-restructure/scripts/install.sh
bash -n .worktrees/environments-restructure/scripts/hyper-trader-manager.sh
```

Expected: both exit 0 with no output.

- [ ] **Step 5: Delete plan file before merge**

```bash
git -C .worktrees/environments-restructure rm docs/superpowers/plans/2026-04-30-environments-restructure.md
git -C .worktrees/environments-restructure commit -m "chore: remove environments-restructure plan"
```

---

## Notes

- **`deploy/docker-compose.pebble.yml`** is deleted without replacement. It was an overlay file for a two-compose approach; `environments/dev-ssl/docker-compose.yml` is already the merged single file.
- **`deploy/.env.api.development` / `.env.api.pebble`** (gitignored, on disk) are not touched by the plan — they're local dev state and will be left behind when `deploy/` tracked files are removed. Developers will recreate from the new example files.
- **`data/traefik-pebble/.gitignore`** had a bug: it listed `dynamic/*` without `!dynamic/10-tls.yml`, yet `10-tls.yml` was tracked (added before the gitignore existed). The new `environments/dev-ssl/traefik/.gitignore` fixes this by explicitly including `!dynamic/10-tls.yml`.
- **`traefik-acme-init`** service in `environments/dev-ssl/docker-compose.yml` originates from `feature/ssl-wizard-restart-ux`. It replaces the need for the manual `touch acme.json && chmod 600` setup step.
- **VPS layout after install**: `/opt/hyper-trader/docker-compose.yml`, `.env`, `api.env`, `traefik/traefik.yml`, `traefik/dynamic/00-bootstrap.yml`, `traefik/acme.json`. No `deploy/` or `data/` subdirs.
