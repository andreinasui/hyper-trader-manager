# HyperTrader Manager

Self-hosted manager for HyperTrader instances: FastAPI backend, SolidJS dashboard, Docker-based trader runtime, and VPS deployment tooling.

## What Is Here

| Path | Purpose |
|---|---|
| `api/` | FastAPI API, SQLite, auth, Docker/Swarm trader management |
| `web/` | SolidJS dashboard built with Solid Start, TanStack Solid Query, Tailwind CSS |
| `environments/dev/` | Local Docker Compose stack for Traefik + API + Web |
| `environments/prod/` | Production Compose files downloaded by installer |
| `helper/` | Short-lived update helper container with rollback support |
| `scripts/` | Install, release, update-test, and stack management scripts |
| `docs/` | Quick start, development, and SSL testing docs |

## Quick Start

### Local Development

```bash
just install
cp api/.env.example api/.env.development

# terminal 1
just api

# terminal 2
just web
```

Open `http://localhost:3000`. API docs live at `http://localhost:8000/docs`.

More detail: [DEV_SETUP.md](DEV_SETUP.md).

### VPS Production

```bash
curl -sSL https://raw.githubusercontent.com/andreinasui/hyper-trader-manager/main/scripts/install.sh | sudo bash
sudo nano /opt/hyper-trader/api.env
hyper-trader-manager start
```

Open your server in a browser. Production first-run flow configures Let's Encrypt HTTPS, then admin setup.

More detail: [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Stack

| Service | Tech | Notes |
|---|---|---|
| `traefik` | Traefik v3 | Routes `/*` to web and `/api/*` to API, handles HTTPS |
| `api` | Python 3.11+, FastAPI, SQLAlchemy, SQLite | Manages auth, traders, SSL setup, updates |
| `web` | SolidJS, Solid Start, TypeScript, Tailwind CSS | Dashboard on port `3000` internally |
| `helper` | Bash + Docker CLI | Runs self-update flow and rollback |

Trader private keys are stored as Docker Swarm secrets. Swarm mode is initialized when needed.

## Common Commands

```bash
# repo root
just install          # install api + web dependencies
just api              # run backend on :8000
just web              # run frontend on :3000
just release 0.2.13   # create release artifacts

# api/
just test
just lint
just format

# web/
pnpm test
pnpm build
pnpm test:e2e
```

Production host commands after install:

```bash
hyper-trader-manager start
hyper-trader-manager status
hyper-trader-manager logs api
hyper-trader-manager update
hyper-trader-manager restore-backup <version>
```

## Data

| Environment | Location |
|---|---|
| Local direct dev | `api/data/hypertrader.db` |
| Local Compose dev | `environments/dev/sqlitedb/` and `environments/dev/traefik/` |
| Production | Docker volumes plus `/opt/hyper-trader/traefik/` host config |

## HTTPS

Production requires a real domain for Let's Encrypt. Ports `80` and `443` must be reachable. Admin bootstrap is blocked until HTTPS is configured, so admin credentials are not sent over plaintext HTTP.

Local direct dev runs over HTTP. For local SSL testing, see [docs/SSL_LOCAL_TESTING.md](docs/SSL_LOCAL_TESTING.md).

## More Docs

- [docs/QUICKSTART.md](docs/QUICKSTART.md) — local and VPS setup
- [DEV_SETUP.md](DEV_SETUP.md) — contributor setup and commands
- [helper/README.md](helper/README.md) — update helper behavior
- [AGENTS.md](AGENTS.md) — repo conventions for agents
