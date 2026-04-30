# Development Setup Guide

Complete guide for setting up the HyperTrader platform locally.

## Prerequisites

### Required Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| **uv** | Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **nodenv** | Node.js version manager | `brew install nodenv` |
| **pnpm** | Node.js package manager | `npm install -g pnpm` |
| **just** | Command runner | `brew install just` |

### Verify Installation
```bash
uv --version
nodenv --version
pnpm --version
just --version
```

## Quick Start

### 1. Install Node.js 22.12.0
```bash
nodenv install 22.12.0
cd web && node --version  # Should show v22.12.0
```

### 2. Install Dependencies
```bash
just check-prereqs  # Verify prerequisites
just install        # Install all dependencies
```

### 3. Configure Environment
```bash
cd api
cp .env.example .env.development
# Edit api/.env.development if needed (defaults work for local dev)
```

### 4. Start Services (2 terminals)

**Terminal 1 - Backend API:**
```bash
just api  # http://localhost:8000
```
The API creates the SQLite database automatically at `api/data/hypertrader.db`.

**Terminal 2 - Frontend:**
```bash
just web  # http://localhost:3000
```

### 5. Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

## Common Tasks

### Database Operations

The API uses SQLite. The database file is created automatically on first run.

```bash
# Database location
api/data/hypertrader.db

# Reset database (deletes all data)
rm api/data/hypertrader.db
just api  # Recreates the database
```

### Backend Development
```bash
cd api
just dev         # Dev server with hot reload
just test        # Run tests
just lint        # Lint code
just format      # Format code
just check       # Run all checks
```

### Frontend Development
```bash
cd web
just dev         # Dev server with hot reload
just build       # Production build
just preview     # Preview production build
just lint        # Lint code
```

## Testing Authentication

### Bootstrap Admin (First Run)

On first run, the system is uninitialized. Use the setup endpoint or the web UI:

```bash
# Check setup status
curl http://localhost:8000/api/v1/auth/setup-status

# Bootstrap admin via API
curl -X POST http://localhost:8000/api/v1/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Or open http://localhost:3000 and complete the setup wizard.

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

## Troubleshooting

### API Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000
kill -9 <PID>

# Check environment config
cat api/.env.development
```

### Frontend Won't Start
```bash
# Check if port 3000 is in use
lsof -i :3000
kill -9 <PID>

# Reinstall dependencies
cd web && rm -rf node_modules && pnpm install
```

### Authentication Issues
```bash
# Check environment config
cat api/.env.development

# Clear browser storage
# In browser console: localStorage.clear()

# Reset database and re-bootstrap
rm api/data/hypertrader.db
just api
```

### Complete Reset
```bash
rm -rf api/.venv web/node_modules api/data/hypertrader.db
just install
just api  # In terminal 1
just web  # In terminal 2
```

## SSL Configuration (Production)

HyperTrader includes an **SSL Setup Wizard** that guides self-hosted users through configuring HTTPS access. SSL is **only available in production deployments** (`ENVIRONMENT=production`); local development runs over plain HTTP.

### How the SSL Setup Wizard Works

On the first access to a production instance, users are automatically redirected to `/setup/ssl`. The wizard configures HTTPS via **Let's Encrypt** — this is the only supported mode. Self-signed / IP-only certificates are not supported; a real domain is required.

**Wizard flow:**
1. User visits the app for the first time over HTTP (production).
2. App redirects to `/setup/ssl`.
3. User enters their domain name and an email address (used for Let's Encrypt expiry notifications).
4. Backend writes Traefik configuration, requests a certificate via the ACME HTTP-01 challenge, and restarts Traefik.
5. User is redirected to `https://<domain>` and can then create the admin account.

The admin bootstrap endpoint is **gated** on SSL being configured: in production, `POST /api/v1/auth/bootstrap` returns `409 Conflict` until a valid certificate has been provisioned. This guarantees the admin password is never transmitted over plaintext HTTP.

### Let's Encrypt Requirements

Before running the wizard, ensure all of the following are true:

- **Domain name** — You own a domain (or subdomain) and its DNS `A` record points to the public IP address of your server.
- **Port 80 open** — Let's Encrypt's ACME HTTP-01 challenge requires inbound traffic on port 80. Traefik handles the challenge automatically; you only need the port to be reachable.
- **Port 443 open** — HTTPS traffic must be reachable on port 443.
- **No firewall/NAT blocking** — Both ports must be reachable from the public internet (check cloud security groups, router port forwarding, etc.).

> **Note:** Certificate issuance can take up to 60 seconds. Let's Encrypt rate-limits failed attempts (5 failures per account/hostname per hour), so verify DNS propagation and port accessibility *before* running the wizard.

### Reconfiguring SSL

If you need to update the domain or re-issue the certificate, reset the stored SSL configuration:

```bash
# 1. Open the database
sqlite3 data/hypertrader.db

# 2. Delete the SSL config record
DELETE FROM ssl_config;
.quit

# 3. Restart the application
docker compose restart app

# 4. Visit the app — you will be redirected to /setup/ssl again
```

Alternatively, to start completely fresh (including Traefik configs and certs):

```bash
# Remove SSL-related Traefik files
rm -rf data/traefik/

# Reset the SSL config in the database
sqlite3 data/hypertrader.db "DELETE FROM ssl_config;"

# Restart the stack
docker compose restart
```

### SSL File Locations (Production)

| File / Directory | Purpose |
|-----------------|---------|
| `data/traefik/traefik.yml` | Main Traefik static config |
| `data/traefik/dynamic/` | Traefik dynamic routing config |
| `data/traefik/certs/` | Self-signed certificate files |
| `data/traefik/acme.json` | Let's Encrypt certificate store (mode 600) |

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

## Production Deployment

See [README.md](README.md) for production deployment with Docker Compose.

```bash
# Quick production start
cp deploy/.env.example .env
# Edit .env with your settings
docker compose up -d --build
```

## Project Structure

```
hyper-trader-manager/
├── api/                    # Python FastAPI backend
│   ├── justfile            # Backend commands
│   ├── .env.development    # Dev environment config
│   ├── data/               # SQLite database directory
│   │   └── hypertrader.db  # Database file (created on first run)
│   ├── hyper_trader_api/   # Main package
│   │   ├── main.py         # FastAPI app entry
│   │   ├── models/         # SQLAlchemy models
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   └── ...
│   └── tests/              # Backend tests
├── web/                    # React 19 + TanStack frontend
│   ├── justfile            # Frontend commands
│   ├── .env.development    # Dev environment config
│   ├── src/
│   │   ├── routes/         # Page routes
│   │   ├── components/     # React components
│   │   └── lib/            # Utilities
│   └── ...
├── deploy/                 # Production deployment configs
│   ├── traefik/            # Traefik routing config
│   └── .env.example        # Production env template
├── docker-compose.yml      # Production stack
├── justfile                # Root commands
└── DEV_SETUP.md           # This file
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| **Frontend** | React 19, TypeScript, TanStack Router/Query, Tailwind CSS |
| **Production** | Docker Compose, Docker Swarm, Traefik, SQLite |
| **Auth** | Session tokens, password hashing (bcrypt) |
| **Secrets** | Docker Swarm secrets (private keys at `/run/secrets/private_key`) |

## Resources

- **API Docs**: http://localhost:8000/docs
- **TanStack**: https://tanstack.com
- **FastAPI**: https://fastapi.tiangolo.com
- **Project Guide**: AGENTS.md
