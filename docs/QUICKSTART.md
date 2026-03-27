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

# 3. Generate encryption keys for the backend
cd api && just gen-keys
# Copy the output to api/.env.development
cd ..

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
- Create `deploy/.env` with auto-generated secrets
- Set up initial Traefik configuration
- Build and start the Docker stack
- Wait for services to be healthy

### Manual Installation

If you prefer manual setup:

```bash
# 1. Create environment file
cp deploy/.env.example deploy/.env

# 2. Generate a secure encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy the output to ENCRYPTION_KEY in deploy/.env

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

### First-Time Setup (Web UI)

1. Open `http://your-server-ip` in your browser

2. **Admin Setup**: Create your admin account
   - Choose a username and strong password
   - This becomes your login for the dashboard

3. **SSL Setup**: Configure HTTPS access
   - **Option A: Domain + Let's Encrypt** (recommended)
     - Enter your domain name (e.g., `trader.example.com`)
     - Enter email for certificate notifications
     - Traefik automatically obtains a trusted certificate
   - **Option B: IP-only + Self-Signed**
     - No domain required
     - Browser will show security warning (expected)

4. After SSL setup, you'll be redirected to HTTPS

### Environment Variables

Key settings in `deploy/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENCRYPTION_KEY` | Wallet private key encryption (required) | *auto-generated* |
| `DOCKER_GID` | Docker group ID | *auto-detected* |
| `PUBLIC_PORT` | HTTP port | `80` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### SSL Configuration

#### Let's Encrypt Requirements

For automatic trusted certificates:
- Domain's DNS A record must point to your VPS IP
- Ports 80 and 443 must be accessible from the internet
- No firewall blocking inbound HTTP/HTTPS

#### Self-Signed Certificates

For IP-only access:
- No domain required
- Browser shows security warning on first visit
- Click "Advanced" → "Proceed" to continue

#### Reconfigure SSL

To change SSL settings:

```bash
# Delete SSL config from database
sqlite3 data/hypertrader.db "DELETE FROM ssl_config;"

# Restart to trigger SSL wizard
docker compose restart
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

All data is stored in `./data/` on the host:

| Path | Contents |
|------|----------|
| `data/hypertrader.db` | SQLite database |
| `data/traders/` | Trader configuration files |
| `data/traefik/` | Traefik config and SSL certs |
| `data/traefik/acme.json` | Let's Encrypt certificates |
| `data/traefik/certs/` | Self-signed certificates |

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
