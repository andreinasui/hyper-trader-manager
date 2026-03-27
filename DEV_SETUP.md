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
just gen-keys  # Generates JWT_SECRET_KEY and ENCRYPTION_KEY
# Copy output to api/.env.development
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
just gen-keys    # Generate JWT/encryption keys
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
# Check JWT secret is set
cd api && just dev  # Look for config loading in logs

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
| **Production** | Docker Compose, Traefik, SQLite |
| **Auth** | JWT tokens, password hashing (bcrypt) |

## Resources

- **API Docs**: http://localhost:8000/docs
- **TanStack**: https://tanstack.com
- **FastAPI**: https://fastapi.tiangolo.com
- **Project Guide**: AGENTS.md
