# HyperTrader Infrastructure - Development Commands
# Install just: https://github.com/casey/just#installation

set shell := ["bash", "-cu"]

# Default recipe - show help
default:
    @just --list

# ─────────────────────────────────────────────────────────────
# Database Commands
# ─────────────────────────────────────────────────────────────

# Start PostgreSQL and pgAdmin containers
db:
    docker compose -f docker-compose.dev.yml up -d
    @echo ""
    @echo "✓ PostgreSQL running at localhost:5432"
    @echo "✓ pgAdmin running at http://localhost:5050"
    @echo "  Email: admin@hypertrader.local"
    @echo "  Password: admin"

# Stop database containers
db-stop:
    docker compose -f docker-compose.dev.yml down

# Reset database (WARNING: deletes all data)
db-reset:
    docker compose -f docker-compose.dev.yml down -v
    docker compose -f docker-compose.dev.yml up -d
    @echo "✓ Database reset complete"

# View database logs
db-logs:
    docker compose -f docker-compose.dev.yml logs -f postgres

# Connect to PostgreSQL via psql
db-shell:
    docker exec -it hypertrader-postgres psql -U hypertrader -d hypertrader

# ─────────────────────────────────────────────────────────────
# Development Shortcuts (delegate to subdirectories)
# ─────────────────────────────────────────────────────────────

# Run backend API (delegates to api/justfile)
api:
    cd api && just dev

# Run frontend web (delegates to web/justfile)
web:
    cd web && just dev

# Install all dependencies
install:
    cd api && just install-dev
    cd web && just install

# ─────────────────────────────────────────────────────────────
# Docker Build Commands
# ─────────────────────────────────────────────────────────────

# Build API Docker image
build-api:
    docker build -f docker/Dockerfile.api -t hyper-trader-api .

# Build Web Docker image
build-web:
    docker build -f web/Dockerfile -t hyper-trader-web .

# Build all images
build-all: build-api build-web

# ─────────────────────────────────────────────────────────────
# Verification Commands
# ─────────────────────────────────────────────────────────────

# Check development prerequisites
check-prereqs:
    @echo "Checking prerequisites..."
    @command -v docker >/dev/null 2>&1 || { echo "✗ Docker not found"; exit 1; }
    @echo "✓ Docker"
    @command -v just >/dev/null 2>&1 || { echo "✗ just not found"; exit 1; }
    @echo "✓ just"
    @command -v uv >/dev/null 2>&1 || { echo "✗ uv not found"; exit 1; }
    @echo "✓ uv"
    @command -v nodenv >/dev/null 2>&1 || { echo "✗ nodenv not found"; exit 1; }
    @echo "✓ nodenv"
    @command -v pnpm >/dev/null 2>&1 || { echo "✗ pnpm not found (install: npm install -g pnpm)"; exit 1; }
    @echo "✓ pnpm"
    @echo ""
    @echo "All prerequisites installed!"

# ─────────────────────────────────────────────────────────────
# Info Commands
# ─────────────────────────────────────────────────────────────

# Show development URLs
urls:
    @echo "Development URLs:"
    @echo "  Frontend:    http://localhost:3000"
    @echo "  Backend API: http://localhost:8000"
    @echo "  Swagger:     http://localhost:8000/docs"
    @echo "  ReDoc:       http://localhost:8000/redoc"
    @echo "  pgAdmin:     http://localhost:5050"
    @echo "  PostgreSQL:  localhost:5432"

# Show quick start guide
quickstart:
    @echo "Quick Start:"
    @echo ""
    @echo "1. Start database:"
    @echo "   just db"
    @echo ""
    @echo "2. In a new terminal, start backend:"
    @echo "   just api"
    @echo "   # Or: cd api && just dev"
    @echo ""
    @echo "3. In a new terminal, start frontend:"
    @echo "   just web"
    @echo "   # Or: cd web && just dev"
    @echo ""
    @echo "4. Open http://localhost:3000"
