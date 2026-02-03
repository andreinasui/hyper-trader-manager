# Development Setup Guide

Complete guide for setting up the HyperTrader platform locally and deploying to production.

## Prerequisites

### Required Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| **Docker** | PostgreSQL + pgAdmin | `brew install docker` or [docker.com](https://docker.com) |
| **uv** | Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **nodenv** | Node.js version manager | `brew install nodenv` |
| **pnpm** | Node.js package manager | `npm install -g pnpm` |
| **just** | Command runner | `brew install just` |

### Verify Installation
```bash
docker --version && docker compose version
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

### 4. Start Services (3 terminals)

**Terminal 1 - Database:**
```bash
just db  # PostgreSQL:5432, pgAdmin:5050
```

**Terminal 2 - Backend API:**
```bash
just api  # http://localhost:8000
```

**Terminal 3 - Frontend:**
```bash
just web  # http://localhost:3000
```

### 5. Access the Application

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Register new account |
| API Docs | http://localhost:8000/docs | - |
| pgAdmin | http://localhost:5050 | admin@hypertrader.dev / admin |

## Common Tasks

### Database Operations
```bash
just db          # Start PostgreSQL + pgAdmin
just db-stop     # Stop containers
just db-reset    # Reset database (⚠️  deletes all data)
just db-logs     # View logs
just db-shell    # Open psql shell
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

### Register & Login
```bash
# Register with password
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'
```

### Create Admin User (Optional)
```python
from api.database import SessionLocal
from api.models import User
from api.utils.crypto import hash_password

db = SessionLocal()
admin = User(
    email="admin@hypertrader.io",
    password_hash=hash_password("SecurePassword123!"),
    is_admin=True,
    plan_tier="enterprise"
)
db.add(admin)
db.commit()
print("✓ Admin user created!")
```

## Troubleshooting

### Database Issues
```bash
# Connection refused
docker ps | grep postgres  # Check if running
just db-logs               # View logs
just db-stop && just db    # Restart

# Reset database
just db-reset              # ⚠️  Deletes all data
```

### Authentication Issues
```bash
# Check JWT secret is set
python -c "from api.config import get_settings; print(get_settings().jwt_secret_key)"

# Clear browser storage
# In browser console: localStorage.clear()

# Verify token at https://jwt.io
```

### Port Already in Use
```bash
lsof -i :8000     # Find process (or :3000, :5432)
kill -9 <PID>     # Kill process
```

### Complete Reset
```bash
just db-stop
docker compose -f docker-compose.dev.yml down -v
rm -rf api/.venv web/node_modules
just install && just db
```

## Production Deployment

### Build Docker Images
```bash
# Backend
docker build -t ghcr.io/andreinasui/hyper-trader-api:latest -f api/Dockerfile .

# Frontend
cd web
docker build -t ghcr.io/andreinasui/hyper-trader-web:latest .
```

### Kubernetes Deployment
```bash
# Create secrets
kubectl create secret generic hypertrader-secrets \
  --from-literal=jwt-secret-key="<your-jwt-secret>" \
  --from-literal=encryption-key="<your-encryption-key>" \
  --namespace=hyper-trader

# Deploy
kubectl apply -f kubernetes/base/api-deployment.yaml
kubectl apply -f kubernetes/base/web-deployment.yaml

# Verify
kubectl get pods -n hyper-trader
kubectl get svc -n hyper-trader
kubectl get ingress -n hyper-trader

# Access via port-forward (testing)
kubectl port-forward -n hyper-trader svc/hypertrader-web 3000:80
```

## Project Structure

```
hyper-trader-infra/
├── api/                    # Python FastAPI backend
│   ├── justfile            # Backend commands
│   ├── .env.development    # Dev environment config
│   ├── main.py             # FastAPI app entry
│   ├── models/             # SQLAlchemy models
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic
│   └── migrations/         # Database migrations
├── web/                    # React 19 + TanStack frontend
│   ├── justfile            # Frontend commands
│   ├── .env.development    # Dev environment config
│   ├── src/
│   │   ├── routes/         # Page routes
│   │   ├── components/     # React components
│   │   └── lib/            # Utilities
│   └── ...
├── kubernetes/             # K8s manifests
├── docker/                 # Dockerfiles
├── docker-compose.dev.yml  # Local dev services
├── justfile                # Root commands
└── DEV_SETUP.md           # This file
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL |
| **Frontend** | React 19, TypeScript, TanStack Router/Query, Tailwind CSS |
| **Infrastructure** | Docker, Kubernetes, PostgreSQL |
| **Auth** | JWT tokens, password hashing (bcrypt) |

## Resources

- **API Docs**: http://localhost:8000/docs
- **TanStack**: https://tanstack.com
- **FastAPI**: https://fastapi.tiangolo.com
- **Project Guide**: AGENTS.md

