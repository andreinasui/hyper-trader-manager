# HyperTrader Quick Start Guide

This guide covers two setup scenarios:
1. **[Local Development](#local-development)** — For contributors and developers
2. **[VPS Production](#vps-production-deployment)** — For self-hosted deployments

---

## Local Development

Run the backend and frontend directly on your machine without Docker.

### Prerequisites

| Tool | Purpose | Installation |
|------|---------|--------------|
| **uv** | Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Node.js 22+** | JavaScript runtime | Via `nodenv`, `nvm`, or [nodejs.org](https://nodejs.org) |
| **pnpm** | Node.js package manager | `npm install -g pnpm` |
| **just** | Command runner | `brew install just` or `cargo install just` |

Verify installation:
```bash
uv --version      # 0.5+
node --version    # v22+
pnpm --version    # 9+
just --version    # 1.0+
```

### Setup Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourorg/hyper-trader-manager.git
cd hyper-trader-manager

# 2. Install all dependencies (backend + frontend)
just install

# 3. Configure environment (defaults work for local dev)
cp api/.env.example api/.env.development

# 4. Start the backend (Terminal 1)
just api
# API runs at http://localhost:8000
# Swagger docs at http://localhost:8000/docs

# 5. Start the frontend (Terminal 2)
just web
# Frontend runs at http://localhost:3000
```

### First-Time Setup

1. Open http://localhost:3000 in your browser
2. You'll see the **Admin Setup** page
3. Create your admin account (username + password)
4. You're in!

> **Note:** SSL setup is skipped in development mode. The SSL wizard only appears in production.

### Development Commands

```bash
# Root commands (from project root)
just install          # Install all dependencies
just api              # Start backend dev server
just web              # Start frontend dev server
just check            # Run all checks (lint + test)

# Backend commands (from api/)
cd api
just dev              # Dev server with hot reload
just test             # Run tests
just lint             # Check code style
just format           # Auto-format code
just check            # Run all quality checks

# Frontend commands (from web/)
cd web
just dev              # Dev server with hot reload
just build            # Production build
just test             # Run unit tests
just typecheck        # TypeScript checks
```

### Database

SQLite database is created automatically at `api/data/hypertrader.db`.

```bash
# Reset database (deletes all data)
rm api/data/hypertrader.db
just api  # Recreates on startup
```

### Troubleshooting

**Port already in use:**
```bash
lsof -i :8000  # Find process using port 8000
lsof -i :3000  # Find process using port 3000
kill -9 <PID>  # Kill the process
```

**Complete reset:**
```bash
rm -rf api/.venv web/node_modules api/data/hypertrader.db
just install
```

---

## VPS Production Deployment

Deploy HyperTrader on a VPS with Docker Compose, Traefik reverse proxy, and automatic SSL.

### Prerequisites

- **VPS** with Ubuntu 22.04+ (or similar Linux)
- **Docker** and **Docker Compose** installed
- **Ports 80 and 443** open (for SSL)
- **(Optional)** Domain name pointing to your VPS IP

### Quick Install

```bash
# 1. SSH into your VPS
ssh user@your-server-ip

# 2. Clone the repository
git clone https://github.com/yourorg/hyper-trader-manager.git
cd hyper-trader-manager

# 3. Run the installer
./scripts/install.sh
```

The installer will:
- Check prerequisites (Docker, Docker Compose)
- Create `/opt/hyper-trader/.env` from the downloaded example
- Set up initial Traefik configuration
- Build and start the Docker stack
- Wait for services to be healthy

### Manual Installation

If you prefer manual setup:

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

### First-Time Setup (Web UI)

1. Open `http://your-server-ip` (or `http://your-domain`) in your browser

2. **SSL Setup**: Configure HTTPS first — you'll be automatically redirected to `/setup/ssl`
   - Enter your domain name (e.g., `trader.example.com`)
   - Enter email for Let's Encrypt expiry notifications
   - Traefik automatically obtains a trusted certificate via ACME HTTP-01 (~60 seconds)
   - You are then redirected to `https://your-domain`

3. **Admin Setup**: Once on HTTPS, create your admin account
   - Choose a username and strong password
   - This becomes your login for the dashboard

> **Note:** The admin bootstrap endpoint is gated on SSL being configured — you cannot create the admin user over plaintext HTTP. A real domain with public DNS is required; self-signed / IP-only deployments are not supported.

### Environment Variables

Key settings in `/opt/hyper-trader/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKER_GID` | Docker group ID | *auto-detected* |
| `PUBLIC_PORT` | HTTP port | `80` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

> **Note:** Private keys for trader instances are stored as Docker Swarm secrets — no `ENCRYPTION_KEY` is needed. Docker Swarm mode is initialized automatically by the API when the first trader is created.

### SSL Configuration

#### Let's Encrypt Requirements

HyperTrader uses Let's Encrypt for trusted HTTPS certificates. **A real domain is required** — self-signed / IP-only deployments are not supported.

- Domain's DNS A record must point to your VPS IP
- Ports 80 and 443 must be accessible from the internet
- No firewall blocking inbound HTTP/HTTPS
- Certificate issuance via ACME HTTP-01 takes up to 60 seconds

#### Reconfigure SSL

To change the domain or force re-issuance:

```bash
# Delete SSL config from database (database is in the hypertrader-data Docker named volume)
docker exec hypertrader-api sqlite3 /app/data/hypertrader.db "DELETE FROM ssl_config;"

# Restart to trigger SSL wizard
hyper-trader-manager restart
```

### Operations

```bash
# View logs
docker compose logs -f
docker compose logs -f api   # API only
docker compose logs -f web   # Frontend only

# Restart services
docker compose restart

# Stop everything
docker compose down

# Update to latest version
git pull
docker compose up -d --build

# Backup
./scripts/backup.sh
```

### Data Persistence

All data is stored under `/opt/hyper-trader/` on the VPS host:

| Path | Contents |
|------|----------|
| `hypertrader-data` (Docker named volume) | SQLite database and trader configs |
| `traefik/` | Traefik config and SSL certs |
| `traefik/traefik.yml` | Active Traefik static config |
| `traefik/dynamic/` | Traefik dynamic routing config |
| `traefik/acme.json` | Let's Encrypt certificates (mode 600) |
| `traefik/certs/` | Self-signed certificate files |

### Firewall Setup

If using `ufw`:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

If using cloud provider (AWS, GCP, etc.), ensure security group allows:
- Inbound TCP 80 (HTTP)
- Inbound TCP 443 (HTTPS)
- Inbound TCP 22 (SSH)

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              VPS / Server               │
                    │                                         │
    :80/:443        │   ┌─────────┐                           │
 ───────────────────┼──►│ Traefik │                           │
                    │   └────┬────┘                           │
                    │        │                                │
                    │   ┌────┴────┐                           │
                    │   │         │                           │
                    │   ▼         ▼                           │
                    │ /api/*    /*                            │
                    │   │         │                           │
                    │   ▼         ▼                           │
                    │ ┌─────┐  ┌─────┐                        │
                    │ │ API │  │ Web │                        │
                    │ │:8000│  │ :80 │                        │
                    │ └──┬──┘  └─────┘                        │
                    │    │                                    │
                    │    ▼                                    │
                    │ ┌──────────────┐  ┌──────────────────┐  │
                    │ │ SQLite DB    │  │ Docker Socket    │  │
                    │ │ data/*.db    │  │ (trader mgmt)    │  │
                    │ └──────────────┘  └──────────────────┘  │
                    └─────────────────────────────────────────┘
```

| Service | Port | Purpose |
|---------|------|---------|
| Traefik | 80, 443 | Reverse proxy, SSL termination |
| API | 8000 (internal) | FastAPI backend |
| Web | 80 (internal) | React frontend (nginx) |

---

## Next Steps

- **Local Dev**: See [DEV_SETUP.md](../DEV_SETUP.md) for detailed development guide
- **Operations**: See [OPERATIONS.md](OPERATIONS.md) for day-to-day management
- **API Docs**: Visit `/docs` on your running instance for Swagger UI
