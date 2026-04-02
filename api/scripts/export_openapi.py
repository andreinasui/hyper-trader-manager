#!/usr/bin/env python3
"""
Export OpenAPI schema from FastAPI app without running the server.

This script generates the OpenAPI JSON schema directly from the FastAPI app
definition, bypassing the lifespan hooks that require database initialization.

Usage:
    uv run python scripts/export_openapi.py [output_path]
    
If no output path is provided, prints to stdout.
"""

import json
import sys
from pathlib import Path


def get_openapi_schema() -> dict:
    """
    Generate OpenAPI schema from the FastAPI app.
    
    This imports only the necessary components to generate the schema
    without triggering database connections or other side effects.
    """
    # Import FastAPI app - the schema is generated from route definitions
    # without needing to run the lifespan handler
    from fastapi.openapi.utils import get_openapi
    
    from hyper_trader_api.main import app
    
    # Generate OpenAPI schema using FastAPI's built-in utility
    # This uses the app's metadata and route definitions
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )


def main() -> None:
    """Export OpenAPI schema to file or stdout."""
    schema = get_openapi_schema()
    schema_json = json.dumps(schema, indent=2)
    
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(schema_json)
        print(f"OpenAPI schema exported to {output_path}", file=sys.stderr)
    else:
        print(schema_json)


if __name__ == "__main__":
    main()
