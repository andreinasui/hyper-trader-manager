# HyperTrader Manager

Management application for HyperTrader instances — backend API and web dashboard.

## Self-Hosted Deployment (v1)

Run the full HyperTrader stack on a single VPS with Docker Compose and Traefik.

> **New to self-hosted?** See the [Quick Start](docs/SELF_HOSTED_QUICKSTART.md) for step-by-step instructions.
> For day-to-day operations see [Operations Guide](docs/SELF_HOSTED_OPERATIONS.md).

### Stack

| Service   | Description                            | Accessible at             |
|-----------|----------------------------------------|---------------------------|
| `traefik` | Reverse proxy, routes requests         | `:80` (or `PUBLIC_PORT`)  |
| `api`     | FastAPI backend (uvicorn)              | `/api/*`                  |
| `web`     | React frontend (nginx, static assets)  | `/*`                      |
| `data/`   | SQLite DB + trader configs (host volume) | —                       |

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourorg/hyper-trader-manager.git
cd hyper-trader-manager

# 2. Run the installer (guides you through config)
./scripts/install-selfhosted.sh
```

Or do it manually:

```bash
# 2a. Copy and edit environment file
cp deploy/.env.selfhosted.example .env.selfhosted
#    Edit .env.selfhosted — set SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, DOCKER_GID

# 2b. Start the stack
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d --build

# 2c. Verify
curl http://localhost/health
curl http://localhost/api/v1/auth/setup-status
```

Open `http://your-server-ip` in a browser to complete first-run setup.

### Configuration

All settings live in `.env.selfhosted` (copied from `deploy/.env.selfhosted.example`):

| Variable                   | Default                   | Description                                                    |
|----------------------------|---------------------------|----------------------------------------------------------------|
| `PUBLIC_PORT`              | `80`                      | Host port to expose                                            |
| `SECRET_KEY`               | —                         | JWT signing secret (**required** — `openssl rand -hex 32`)    |
| `ADMIN_EMAIL`              | `admin@example.com`       | Admin account email (created on first start)                   |
| `ADMIN_PASSWORD`           | —                         | Admin account password (**required**)                          |
| `DOCKER_GID`               | `999`                     | Docker group GID on the host (`getent group docker | cut -d: -f3`) |
| `DOCKER_SOCKET`            | `/var/run/docker.sock`    | Docker socket path                                             |
| `TRADER_NETWORK`           | `hypertrader_default`     | Docker network for trader containers                           |
| `LOG_LEVEL`                | `INFO`                    | API log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)            |

### Data Persistence

All persistent data is written to `./data/` on the host:

| Path                | Contents                        |
|---------------------|---------------------------------|
| `data/db.sqlite`    | SQLite database                 |
| `data/traders/`     | Trader configuration files      |

### Updating

```bash
./scripts/upgrade-selfhosted.sh
```

Or manually:

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml build --pull
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d
```

### Backup

```bash
./scripts/backup-selfhosted.sh
```

Saves a timestamped archive to `./backups/` containing the SQLite database, trader configs, and a redacted copy of the env file.

---

## Security Notice (v1)

v1 is **HTTP only**. Login credentials are transmitted in plain text.

Recommended mitigations:
- restrict access with a VPS / cloud firewall to trusted IPs
- place behind a secure reverse proxy or VPN for production use

---

## Development

See [DEV_SETUP.md](DEV_SETUP.md) for local development setup.

### Project Structure

| Directory | Description | Tech Stack |
|-----------|-------------|------------|
| `/api`    | Backend API | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| `/web`    | Frontend    | React 19, TypeScript, TanStack Router/Query, Tailwind CSS |
| `/deploy` | Deployment configs | Docker Compose, Traefik |
| `/scripts`| Operational scripts | Bash |
| `/docs`   | Documentation | Markdown |

### Components

- **api/**: FastAPI backend for trader management (SQLite, JWT auth, Docker runtime)
- **web/**: React/Vite frontend for monitoring and controlling traders
- **deploy/traefik/**: Traefik dynamic routing configuration
- **scripts/**: Install, upgrade, and backup automation
