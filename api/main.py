"""
HyperTrader API - Main Application

Multi-tenant trading bot management platform.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import text

from api.config import get_settings
from api.database import engine
from api.routers import auth_router, traders_router, admin_router
from api.workers import start_reconciliation, stop_reconciliation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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

    # Verify database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

    # Start reconciliation worker only if K8s is enabled
    if settings.k8s_enabled:
        logger.info("Starting reconciliation worker...")
        try:
            start_reconciliation()
            logger.info("Reconciliation worker started")
        except Exception as e:
            logger.error(f"Failed to start reconciliation worker: {e}")
            # Continue startup - reconciliation is not critical for API operation
    else:
        logger.info("Kubernetes disabled - reconciliation worker not started")

    logger.info("HyperTrader API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down HyperTrader API...")

    # Stop reconciliation worker
    logger.info("Stopping reconciliation worker...")
    stop_reconciliation()

    engine.dispose()
    logger.info("HyperTrader API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="HyperTrader API",
    description=(
        "Multi-tenant trading bot management platform.\n\n"
        "## Authentication\n\n"
        "All endpoints (except `/api/v1/auth/register` and `/health`) require API key authentication.\n\n"
        "Include your API key in the `X-API-Key` header:\n\n"
        "```\nX-API-Key: ht_your_api_key_here\n```\n\n"
        "## Getting Started\n\n"
        "1. Register at `POST /api/v1/auth/register` to get your API key\n"
        "2. Create a trader at `POST /api/v1/traders/`\n"
        "3. Monitor with `GET /api/v1/traders/{id}/status` and `GET /api/v1/traders/{id}/logs`\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware (configure for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
            elif field_name == "private_key":
                error_msg = "Private key must be a valid Ethereum private key (0x followed by 64 hexadecimal characters)"
            else:
                error_msg = f"Invalid format for {field_name}"
        
        errors.append({
            "field": field_path,
            "message": error_msg,
            "type": error_type,
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": f"Validation error in {errors[0]['field']}: {errors[0]['message']}" if len(errors) == 1 else "Multiple validation errors",
            "errors": errors,
        },
    )


# Include routers
app.include_router(auth_router)
app.include_router(traders_router)
app.include_router(admin_router)


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check",
    description="Check if the API is running and database is connected.",
)
async def health_check():
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
async def root():
    """Root endpoint - redirects to docs."""
    return {
        "message": "HyperTrader API",
        "docs": "/docs",
        "health": "/health",
    }
