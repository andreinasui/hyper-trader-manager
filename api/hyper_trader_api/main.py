"""
HyperTrader API - Main Application

Multi-tenant trading bot management platform.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from hyper_trader_api.config import get_settings
from hyper_trader_api.database import engine
from hyper_trader_api.db.bootstrap import bootstrap_database
from hyper_trader_api.routers import auth_router, traders_router
from hyper_trader_api.workers import start_reconciliation, stop_reconciliation

settings = get_settings()

# Configure logging based on settings
log_level = getattr(logging, settings.log_level)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    datefmt="%H:%M:%S",
    force=True,  # Override existing configurations
)

# Configure SQLAlchemy logging
# In debug mode: show SQL queries at DEBUG level
# In production: only show warnings and errors
if settings.debug:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
else:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"Logging configured at {settings.log_level} level")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Runs on startup:
    - Verify database connection
    - Start reconciliation worker if K8s is enabled

    Runs on shutdown:
    - Stop reconciliation worker
    - Cleanup resources
    """
    # Startup
    logger.info("Starting HyperTrader API...")
    logger.debug(f"Settings loaded: debug={settings.debug}, runtime_mode={settings.runtime_mode}")

    # Initialize database (create tables if they don't exist)
    try:
        logger.debug("Bootstrapping database...")
        bootstrap_database(engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Start reconciliation worker for Docker runtime
    if settings.runtime_mode == "docker":
        logger.info("Starting reconciliation worker for Docker runtime...")
        try:
            start_reconciliation()
            logger.info("Reconciliation worker started")
        except Exception as e:
            logger.error(f"Failed to start reconciliation worker: {e}")
            # Continue startup - reconciliation is not critical for API operation
    else:
        logger.warning(f"Unknown runtime_mode: {settings.runtime_mode}")

    logger.info("HyperTrader API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down HyperTrader API...")

    # Stop reconciliation worker
    logger.info("Stopping reconciliation worker...")
    stop_reconciliation()  # type: ignore[no-untyped-call]

    engine.dispose()
    logger.info("HyperTrader API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="HyperTrader API",
    description=(
        "Self-hosted trading bot management platform.\n\n"
        "## Authentication\n\n"
        "This API uses local username/password authentication with session tokens.\n\n"
        "### Initial Setup\n\n"
        "1. Check system status: `GET /api/v1/auth/setup-status`\n"
        "2. Bootstrap first admin: `POST /api/v1/auth/bootstrap`\n"
        "3. Login: `POST /api/v1/auth/login`\n\n"
        "### Using the API\n\n"
        "Include your access token in the `Authorization` header:\n\n"
        "```\nAuthorization: Bearer <access_token>\n```\n\n"
        "## Getting Started\n\n"
        "1. Bootstrap the system with an admin user\n"
        "2. Login to get your access token\n"
        "3. Create a trader at `POST /api/v1/traders/`\n"
        "4. Monitor with `GET /api/v1/traders/{id}/status` and `GET /api/v1/traders/{id}/logs`\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Custom handler for Pydantic validation errors.

    Formats validation errors to be more user-friendly by:
    - Identifying which field failed validation
    - Providing human-readable error messages instead of regex patterns
    """
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_msg = error["msg"]
        error_type = error["type"]

        # Make regex pattern errors more readable
        if error_type == "string_pattern_mismatch":
            field_name = error["loc"][-1] if error["loc"] else "field"
            if field_name == "wallet_address":
                error_msg = "Wallet address must be a valid Ethereum address (0x followed by 40 hexadecimal characters)"
            else:
                error_msg = f"Invalid format for {field_name}"

        errors.append(
            {
                "field": field_path,
                "message": error_msg,
                "type": error_type,
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": (
                f"Validation error in {errors[0]['field']}: {errors[0]['message']}"
                if len(errors) == 1
                else "Multiple validation errors"
            ),
            "errors": errors,
        },
    )


# Include routers
app.include_router(auth_router)
app.include_router(traders_router)
# app.include_router(admin_router)  # Disabled - no admin functionality with Privy auth


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check",
    description="Check if the API is running and database is connected.",
)
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns OK if:
    - API is running
    - Database is connected
    """
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check - database error: {e}")
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": "1.0.0",
    }


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    tags=["Root"],
    summary="API root",
    include_in_schema=False,
)
async def root() -> dict[str, str]:
    """Root endpoint - redirects to docs."""
    return {
        "message": "HyperTrader API",
        "docs": "/docs",
        "health": "/health",
    }
