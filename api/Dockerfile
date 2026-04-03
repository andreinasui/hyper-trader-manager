# HyperTrader API Dockerfile
# Multi-stage build with uv for fast dependency installation
# Self-hosted edition: SQLite + Docker SDK, no K8s/PostgreSQL deps
# Build context: repo root (.)
# Usage: docker build -f api/docker/Dockerfile.api .

# ============================================
# Build stage - Install dependencies with uv
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build dependencies for compiled packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files from api/ subdirectory
COPY pyproject.toml uv.lock ./
# README.md is referenced in pyproject.toml by hatchling
COPY README.md ./

# Create virtual environment and install dependencies
# --frozen: use exact versions from lockfile
# --no-dev: skip dev dependencies in production
# --no-install-project: skip installing the project package itself for now
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY hyper_trader_api /app/hyper_trader_api

# Install the project itself
RUN uv sync --frozen --no-dev

# ============================================
# Runtime stage - Final image
# ============================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies
# - curl: for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/hyper_trader_api /app/hyper_trader_api

# Create data directory for SQLite and app files
RUN mkdir -p /app/data

# Create non-root user for security
RUN useradd -m -u 1000 hypertrader \
    && chown -R hypertrader:hypertrader /app

# Environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/app/data

# Expose API port
EXPOSE 8000

# Switch to non-root user
USER hypertrader

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API using the venv's uvicorn
CMD ["uvicorn", "hyper_trader_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
