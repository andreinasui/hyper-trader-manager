# SSL Setup Wizard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a web-based SSL setup wizard that configures Traefik for HTTPS (Let's Encrypt or self-signed).

**Architecture:** Backend exposes `/api/v1/setup/ssl` endpoints, writes Traefik config files to shared volume, restarts Traefik via Docker socket. Frontend shows wizard on first access if SSL not configured.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, cryptography (Python), React, TanStack Router/Query, Traefik

---

## Task 1: Add SSLConfig Database Model

**Files:**
- Create: `api/hyper_trader_api/models/ssl_config.py`
- Modify: `api/hyper_trader_api/models/__init__.py`

**Step 1: Create the SSLConfig model**

Create `api/hyper_trader_api/models/ssl_config.py`:

```python
"""SSL configuration model."""
from datetime import datetime
from typing import Literal, Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from hyper_trader_api.database import Base


class SSLConfig(Base):
    """Stores SSL setup configuration. Singleton table (only one row)."""
    
    __tablename__ = "ssl_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "domain" | "ip_only" | null
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    configured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Step 2: Export model from __init__.py**

Add to `api/hyper_trader_api/models/__init__.py`:

```python
from hyper_trader_api.models.ssl_config import SSLConfig
```

And add `SSLConfig` to the `__all__` list.

**Step 3: Run migrations to create table**

```bash
cd api && uv run alembic revision --autogenerate -m "Add SSLConfig table"
cd api && uv run alembic upgrade head
```

**Step 4: Commit**

```bash
git add api/hyper_trader_api/models/
git commit -m "feat: add SSLConfig database model"
```

---

## Task 2: Add SSL Setup Pydantic Schemas

**Files:**
- Create: `api/hyper_trader_api/schemas/ssl_setup.py`
- Modify: `api/hyper_trader_api/schemas/__init__.py`

**Step 1: Create request/response schemas**

Create `api/hyper_trader_api/schemas/ssl_setup.py`:

```python
"""SSL setup request and response schemas."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SSLStatusResponse(BaseModel):
    """Response for SSL setup status check."""
    
    ssl_configured: bool
    mode: Optional[Literal["domain", "ip_only"]] = None
    domain: Optional[str] = None
    configured_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SSLSetupRequest(BaseModel):
    """Request to configure SSL."""
    
    mode: Literal["domain", "ip_only"] = Field(
        ...,
        description="SSL mode: 'domain' for Let's Encrypt, 'ip_only' for self-signed"
    )
    domain: Optional[str] = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$",
        description="Domain name (required if mode is 'domain')"
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="Email for Let's Encrypt notifications (required if mode is 'domain')"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"mode": "domain", "domain": "trader.example.com", "email": "admin@example.com"},
                {"mode": "ip_only"}
            ]
        }
    )


class SSLSetupResponse(BaseModel):
    """Response after SSL setup."""
    
    success: bool
    message: str
    redirect_url: Optional[str] = None
```

**Step 2: Export from __init__.py**

Add to `api/hyper_trader_api/schemas/__init__.py` imports and `__all__`.

**Step 3: Commit**

```bash
git add api/hyper_trader_api/schemas/
git commit -m "feat: add SSL setup Pydantic schemas"
```

---

## Task 3: Add Certificate Generator Utility

**Files:**
- Create: `api/hyper_trader_api/services/cert_generator.py`

**Step 1: Write the certificate generator**

Create `api/hyper_trader_api/services/cert_generator.py`:

```python
"""Self-signed certificate generator."""
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = logging.getLogger(__name__)


class CertGeneratorError(Exception):
    """Certificate generation error."""
    pass


def generate_self_signed_cert(
    cert_path: Path,
    key_path: Path,
    common_name: str = "HyperTrader",
    days_valid: int = 365 * 10,  # 10 years
) -> None:
    """Generate a self-signed certificate and private key.
    
    Args:
        cert_path: Path to write certificate PEM file
        key_path: Path to write private key PEM file
        common_name: Certificate common name
        days_valid: Certificate validity in days
    
    Raises:
        CertGeneratorError: If certificate generation fails
    """
    try:
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Build certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "HyperTrader Self-Hosted"),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=days_valid))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        # Ensure directories exist
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.parent.mkdir(parents=True, exist_ok=True)

        # Write private key
        key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        
        # Write certificate
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        logger.info(f"Generated self-signed certificate: {cert_path}")

    except Exception as e:
        logger.error(f"Failed to generate certificate: {e}")
        raise CertGeneratorError(f"Certificate generation failed: {e}") from e
```

**Step 2: Add missing import**

Add `import ipaddress` at the top of the file.

**Step 3: Add cryptography dependency**

```bash
cd api && uv add cryptography
```

**Step 4: Commit**

```bash
git add api/hyper_trader_api/services/cert_generator.py api/pyproject.toml api/uv.lock
git commit -m "feat: add self-signed certificate generator"
```

---

## Task 4: Add Traefik Config Writer Service

**Files:**
- Create: `api/hyper_trader_api/services/traefik_config.py`

**Step 1: Create Traefik config templates and writer**

Create `api/hyper_trader_api/services/traefik_config.py`:

```python
"""Traefik configuration writer for SSL setup."""
import logging
from pathlib import Path
from typing import Literal

import yaml

logger = logging.getLogger(__name__)


class TraefikConfigError(Exception):
    """Traefik configuration error."""
    pass


TRAEFIK_STATIC_DOMAIN = """\
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

certificatesResolvers:
  letsencrypt:
    acme:
      email: "{email}"
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web

providers:
  file:
    filename: /etc/traefik/dynamic.yml
    watch: true
"""

TRAEFIK_STATIC_IP_ONLY = """\
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

providers:
  file:
    filename: /etc/traefik/dynamic.yml
    watch: true
"""


def _build_dynamic_config_domain(domain: str) -> dict:
    """Build dynamic config for domain mode with Let's Encrypt."""
    return {
        "http": {
            "routers": {
                "health": {
                    "rule": f"Host(`{domain}`) && Path(`/health`)",
                    "service": "api",
                    "entryPoints": ["websecure"],
                    "tls": {"certResolver": "letsencrypt"},
                    "priority": 20,
                },
                "api": {
                    "rule": f"Host(`{domain}`) && PathPrefix(`/api`)",
                    "service": "api",
                    "entryPoints": ["websecure"],
                    "tls": {"certResolver": "letsencrypt"},
                    "priority": 10,
                },
                "web": {
                    "rule": f"Host(`{domain}`)",
                    "service": "web",
                    "entryPoints": ["websecure"],
                    "tls": {"certResolver": "letsencrypt"},
                    "priority": 1,
                },
            },
            "services": {
                "api": {
                    "loadBalancer": {
                        "servers": [{"url": "http://api:8000"}],
                        "healthCheck": {"path": "/health", "interval": "10s", "timeout": "5s"},
                    }
                },
                "web": {
                    "loadBalancer": {
                        "servers": [{"url": "http://web:80"}],
                        "healthCheck": {"path": "/health", "interval": "10s", "timeout": "5s"},
                    }
                },
            },
        }
    }


def _build_dynamic_config_ip_only() -> dict:
    """Build dynamic config for IP-only mode with self-signed cert."""
    return {
        "tls": {
            "certificates": [
                {"certFile": "/certs/cert.pem", "keyFile": "/certs/key.pem"}
            ]
        },
        "http": {
            "routers": {
                "health": {
                    "rule": "Path(`/health`)",
                    "service": "api",
                    "entryPoints": ["websecure"],
                    "tls": {},
                    "priority": 20,
                },
                "api": {
                    "rule": "PathPrefix(`/api`)",
                    "service": "api",
                    "entryPoints": ["websecure"],
                    "tls": {},
                    "priority": 10,
                },
                "web": {
                    "rule": "PathPrefix(`/`)",
                    "service": "web",
                    "entryPoints": ["websecure"],
                    "tls": {},
                    "priority": 1,
                },
            },
            "services": {
                "api": {
                    "loadBalancer": {
                        "servers": [{"url": "http://api:8000"}],
                        "healthCheck": {"path": "/health", "interval": "10s", "timeout": "5s"},
                    }
                },
                "web": {
                    "loadBalancer": {
                        "servers": [{"url": "http://web:80"}],
                        "healthCheck": {"path": "/health", "interval": "10s", "timeout": "5s"},
                    }
                },
            },
        },
    }


class TraefikConfigWriter:
    """Writes Traefik configuration files for SSL setup."""

    def __init__(self, config_dir: Path):
        """Initialize with config directory path.
        
        Args:
            config_dir: Directory containing traefik.yml and dynamic.yml
        """
        self.config_dir = config_dir
        self.static_config_path = config_dir / "traefik.yml"
        self.dynamic_config_path = config_dir / "dynamic.yml"

    def write_domain_config(self, domain: str, email: str) -> None:
        """Write Traefik config for domain mode with Let's Encrypt.
        
        Args:
            domain: The domain name
            email: Email for Let's Encrypt notifications
        
        Raises:
            TraefikConfigError: If writing config fails
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Write static config
            static_config = TRAEFIK_STATIC_DOMAIN.format(email=email)
            self.static_config_path.write_text(static_config)

            # Write dynamic config
            dynamic_config = _build_dynamic_config_domain(domain)
            self.dynamic_config_path.write_text(yaml.dump(dynamic_config, default_flow_style=False))

            logger.info(f"Wrote Traefik domain config for {domain}")

        except Exception as e:
            logger.error(f"Failed to write Traefik config: {e}")
            raise TraefikConfigError(f"Failed to write config: {e}") from e

    def write_ip_only_config(self) -> None:
        """Write Traefik config for IP-only mode with self-signed cert.
        
        Raises:
            TraefikConfigError: If writing config fails
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Write static config
            self.static_config_path.write_text(TRAEFIK_STATIC_IP_ONLY)

            # Write dynamic config
            dynamic_config = _build_dynamic_config_ip_only()
            self.dynamic_config_path.write_text(yaml.dump(dynamic_config, default_flow_style=False))

            logger.info("Wrote Traefik IP-only config")

        except Exception as e:
            logger.error(f"Failed to write Traefik config: {e}")
            raise TraefikConfigError(f"Failed to write config: {e}") from e

    def backup_config(self) -> tuple[str, str] | None:
        """Backup current config files.
        
        Returns:
            Tuple of (static_content, dynamic_content) or None if no config exists
        """
        if not self.static_config_path.exists():
            return None
        
        static = self.static_config_path.read_text() if self.static_config_path.exists() else ""
        dynamic = self.dynamic_config_path.read_text() if self.dynamic_config_path.exists() else ""
        return (static, dynamic)

    def restore_config(self, backup: tuple[str, str]) -> None:
        """Restore config from backup.
        
        Args:
            backup: Tuple of (static_content, dynamic_content)
        """
        static, dynamic = backup
        if static:
            self.static_config_path.write_text(static)
        if dynamic:
            self.dynamic_config_path.write_text(dynamic)
```

**Step 2: Commit**

```bash
git add api/hyper_trader_api/services/traefik_config.py
git commit -m "feat: add Traefik config writer service"
```

---

## Task 5: Add SSL Setup Service

**Files:**
- Create: `api/hyper_trader_api/services/ssl_setup_service.py`

**Step 1: Create the orchestration service**

Create `api/hyper_trader_api/services/ssl_setup_service.py`:

```python
"""SSL setup service - orchestrates SSL configuration."""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import docker
from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.models import SSLConfig
from hyper_trader_api.services.cert_generator import generate_self_signed_cert, CertGeneratorError
from hyper_trader_api.services.traefik_config import TraefikConfigWriter, TraefikConfigError

logger = logging.getLogger(__name__)


class SSLSetupError(Exception):
    """SSL setup error."""
    pass


class SSLSetupService:
    """Service for configuring SSL/TLS."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.settings = get_settings()
        
        # Paths for Traefik config and certs
        self.traefik_config_dir = Path(self.settings.data_dir) / "traefik"
        self.certs_dir = Path(self.settings.data_dir) / "traefik" / "certs"
        
        self.config_writer = TraefikConfigWriter(self.traefik_config_dir)

    def get_ssl_config(self) -> Optional[SSLConfig]:
        """Get current SSL configuration."""
        return self.db.query(SSLConfig).filter(SSLConfig.id == 1).first()

    def is_ssl_configured(self) -> bool:
        """Check if SSL has been configured."""
        config = self.get_ssl_config()
        return config is not None and config.mode is not None

    def configure_domain_ssl(self, domain: str, email: str) -> str:
        """Configure SSL with Let's Encrypt for a domain.
        
        Args:
            domain: The domain name
            email: Email for Let's Encrypt notifications
            
        Returns:
            The HTTPS URL to redirect to
            
        Raises:
            SSLSetupError: If configuration fails
        """
        backup = self.config_writer.backup_config()
        
        try:
            # Write Traefik config
            self.config_writer.write_domain_config(domain, email)
            
            # Create acme.json with correct permissions
            acme_path = self.traefik_config_dir / "acme.json"
            if not acme_path.exists():
                acme_path.touch(mode=0o600)
            
            # Restart Traefik
            self._restart_traefik()
            
            # Save to database
            self._save_config(mode="domain", domain=domain, email=email)
            
            return f"https://{domain}"

        except Exception as e:
            logger.error(f"SSL domain setup failed: {e}")
            if backup:
                self.config_writer.restore_config(backup)
            raise SSLSetupError(f"Failed to configure SSL: {e}") from e

    def configure_ip_only_ssl(self) -> str:
        """Configure SSL with self-signed certificate for IP-only access.
        
        Returns:
            Message about self-signed cert (user accesses via IP)
            
        Raises:
            SSLSetupError: If configuration fails
        """
        backup = self.config_writer.backup_config()
        
        try:
            # Generate self-signed certificate
            cert_path = self.certs_dir / "cert.pem"
            key_path = self.certs_dir / "key.pem"
            generate_self_signed_cert(cert_path, key_path)
            
            # Write Traefik config
            self.config_writer.write_ip_only_config()
            
            # Restart Traefik
            self._restart_traefik()
            
            # Save to database
            self._save_config(mode="ip_only", domain=None, email=None)
            
            return "https://<your-server-ip>"

        except CertGeneratorError as e:
            logger.error(f"Certificate generation failed: {e}")
            raise SSLSetupError(f"Failed to generate certificate: {e}") from e
        except Exception as e:
            logger.error(f"SSL IP-only setup failed: {e}")
            if backup:
                self.config_writer.restore_config(backup)
            raise SSLSetupError(f"Failed to configure SSL: {e}") from e

    def _restart_traefik(self) -> None:
        """Restart Traefik container via Docker socket."""
        try:
            client = docker.from_env()
            container = client.containers.get("hypertrader-traefik")
            container.restart(timeout=30)
            logger.info("Restarted Traefik container")
        except docker.errors.NotFound:
            raise SSLSetupError("Traefik container not found. Is Docker Compose running?")
        except docker.errors.APIError as e:
            raise SSLSetupError(f"Failed to restart Traefik: {e}")

    def _save_config(
        self,
        mode: Literal["domain", "ip_only"],
        domain: Optional[str],
        email: Optional[str],
    ) -> None:
        """Save SSL configuration to database."""
        config = self.get_ssl_config()
        
        if config is None:
            config = SSLConfig(id=1)
            self.db.add(config)
        
        config.mode = mode
        config.domain = domain
        config.email = email
        config.configured_at = datetime.now(timezone.utc)
        
        self.db.commit()
```

**Step 2: Add docker dependency**

```bash
cd api && uv add docker
```

**Step 3: Commit**

```bash
git add api/hyper_trader_api/services/ssl_setup_service.py api/pyproject.toml api/uv.lock
git commit -m "feat: add SSL setup orchestration service"
```

---

## Task 6: Add SSL Setup Router

**Files:**
- Create: `api/hyper_trader_api/routers/ssl_setup.py`
- Modify: `api/hyper_trader_api/main.py`

**Step 1: Create the router**

Create `api/hyper_trader_api/routers/ssl_setup.py`:

```python
"""SSL setup router for initial HTTPS configuration."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from hyper_trader_api.database import get_db
from hyper_trader_api.schemas.ssl_setup import (
    SSLSetupRequest,
    SSLSetupResponse,
    SSLStatusResponse,
)
from hyper_trader_api.services.ssl_setup_service import SSLSetupService, SSLSetupError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/setup",
    tags=["Setup"],
)


@router.get(
    "/ssl-status",
    response_model=SSLStatusResponse,
    summary="Check SSL configuration status",
    description="Check if SSL/HTTPS has been configured for this instance.",
)
async def get_ssl_status(
    db: Session = Depends(get_db),
) -> SSLStatusResponse:
    """Check if SSL has been configured."""
    service = SSLSetupService(db)
    config = service.get_ssl_config()
    
    if config is None or config.mode is None:
        return SSLStatusResponse(ssl_configured=False)
    
    return SSLStatusResponse(
        ssl_configured=True,
        mode=config.mode,
        domain=config.domain,
        configured_at=config.configured_at,
    )


@router.post(
    "/ssl",
    response_model=SSLSetupResponse,
    summary="Configure SSL/HTTPS",
    description="Configure SSL with either Let's Encrypt (domain) or self-signed certificate (IP-only).",
)
async def configure_ssl(
    request: SSLSetupRequest,
    db: Session = Depends(get_db),
) -> SSLSetupResponse:
    """Configure SSL for this instance."""
    service = SSLSetupService(db)
    
    # Check if already configured
    if service.is_ssl_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSL is already configured. Reconfiguration is not supported.",
        )
    
    # Validate domain mode requirements
    if request.mode == "domain":
        if not request.domain:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Domain is required when mode is 'domain'",
            )
        if not request.email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email is required when mode is 'domain' (for Let's Encrypt)",
            )
    
    try:
        if request.mode == "domain":
            redirect_url = service.configure_domain_ssl(request.domain, request.email)
            return SSLSetupResponse(
                success=True,
                message=f"SSL configured with Let's Encrypt for {request.domain}",
                redirect_url=redirect_url,
            )
        else:
            service.configure_ip_only_ssl()
            return SSLSetupResponse(
                success=True,
                message="SSL configured with self-signed certificate. Your browser will show a security warning on first visit - this is expected.",
                redirect_url=None,  # User needs to access via their IP
            )
    
    except SSLSetupError as e:
        logger.error(f"SSL setup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
```

**Step 2: Register router in main.py**

Add to `api/hyper_trader_api/main.py`:

```python
from hyper_trader_api.routers.ssl_setup import router as ssl_setup_router

# In the router registration section:
app.include_router(ssl_setup_router)
```

**Step 3: Commit**

```bash
git add api/hyper_trader_api/routers/ssl_setup.py api/hyper_trader_api/main.py
git commit -m "feat: add SSL setup API endpoints"
```

---

## Task 7: Update Docker Compose for SSL Support

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Update Traefik service configuration**

Modify the `traefik` service in `docker-compose.yml` to:
- Add port 443 mapping
- Mount config directory from data volume
- Mount certs directory
- Mount acme.json for Let's Encrypt

```yaml
  traefik:
    image: traefik:v3.3
    container_name: hypertrader-traefik
    restart: unless-stopped
    ports:
      - "${PUBLIC_PORT:-80}:80"
      - "443:443"
    volumes:
      - ./data/traefik:/etc/traefik:ro
      - ./data/traefik/certs:/certs:ro
      - ./data/traefik/acme.json:/letsencrypt/acme.json
    networks:
      - hypertrader
    healthcheck:
      test: ["CMD", "traefik", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 3
```

**Step 2: Update api service to mount data/traefik for writing**

The api service already has `./data:/app/data` mounted, so it can write to `./data/traefik`.

**Step 3: Create initial Traefik config for HTTP mode**

Create `deploy/traefik-initial/traefik.yml` (HTTP-only initial config):

```yaml
entryPoints:
  web:
    address: ":80"

providers:
  file:
    filename: /etc/traefik/dynamic.yml
    watch: true
```

Copy `deploy/traefik/dynamic.yml` to `data/traefik/dynamic.yml` on first run.

**Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: update docker-compose for SSL support"
```

---

## Task 8: Add Frontend SSL Setup API Client

**Files:**
- Create: `web/src/api/ssl-setup.ts`

**Step 1: Create API client functions**

Create `web/src/api/ssl-setup.ts`:

```typescript
import { apiClient } from "./client";

export interface SSLStatusResponse {
  ssl_configured: boolean;
  mode?: "domain" | "ip_only";
  domain?: string;
  configured_at?: string;
}

export interface SSLSetupRequest {
  mode: "domain" | "ip_only";
  domain?: string;
  email?: string;
}

export interface SSLSetupResponse {
  success: boolean;
  message: string;
  redirect_url?: string;
}

export async function getSSLStatus(): Promise<SSLStatusResponse> {
  const response = await apiClient.get<SSLStatusResponse>("/api/v1/setup/ssl-status");
  return response.data;
}

export async function configureSSL(request: SSLSetupRequest): Promise<SSLSetupResponse> {
  const response = await apiClient.post<SSLSetupResponse>("/api/v1/setup/ssl", request);
  return response.data;
}
```

**Step 2: Commit**

```bash
git add web/src/api/ssl-setup.ts
git commit -m "feat: add SSL setup API client"
```

---

## Task 9: Create SSL Setup Wizard Page

**Files:**
- Create: `web/src/routes/setup/ssl.tsx`

**Step 1: Create the setup wizard page**

Create `web/src/routes/setup/ssl.tsx`:

```tsx
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getSSLStatus, configureSSL, SSLSetupRequest } from "../../api/ssl-setup";

export const Route = createFileRoute("/setup/ssl")({
  component: SSLSetupWizard,
});

function SSLSetupWizard() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"domain" | "ip_only">("domain");
  const [domain, setDomain] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const statusQuery = useQuery({
    queryKey: ["ssl-status"],
    queryFn: getSSLStatus,
  });

  const setupMutation = useMutation({
    mutationFn: configureSSL,
    onSuccess: (data) => {
      if (data.redirect_url) {
        // Redirect to HTTPS URL
        window.location.href = data.redirect_url;
      } else {
        // IP-only mode - show success message
        navigate({ to: "/setup/ssl-complete" });
      }
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  // Redirect if already configured
  if (statusQuery.data?.ssl_configured) {
    navigate({ to: "/" });
    return null;
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const request: SSLSetupRequest = { mode };
    if (mode === "domain") {
      if (!domain.trim()) {
        setError("Domain is required");
        return;
      }
      if (!email.trim()) {
        setError("Email is required for Let's Encrypt");
        return;
      }
      request.domain = domain.trim();
      request.email = email.trim();
    }

    setupMutation.mutate(request);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            SSL Setup
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Configure secure HTTPS access for your dashboard
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="flex items-center space-x-3">
                <input
                  type="radio"
                  name="mode"
                  value="domain"
                  checked={mode === "domain"}
                  onChange={() => setMode("domain")}
                  className="h-4 w-4 text-indigo-600"
                />
                <span className="text-sm font-medium text-gray-900">
                  I have a domain name (recommended)
                </span>
              </label>
              <p className="ml-7 text-sm text-gray-500">
                Uses Let's Encrypt for trusted SSL certificates
              </p>
            </div>

            {mode === "domain" && (
              <div className="ml-7 space-y-4">
                <div>
                  <label htmlFor="domain" className="block text-sm font-medium text-gray-700">
                    Domain name
                  </label>
                  <input
                    type="text"
                    id="domain"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    placeholder="trader.example.com"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    Email (for Let's Encrypt notifications)
                  </label>
                  <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@example.com"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="flex items-center space-x-3">
                <input
                  type="radio"
                  name="mode"
                  value="ip_only"
                  checked={mode === "ip_only"}
                  onChange={() => setMode("ip_only")}
                  className="h-4 w-4 text-indigo-600"
                />
                <span className="text-sm font-medium text-gray-900">
                  IP address only
                </span>
              </label>
              <p className="ml-7 text-sm text-gray-500">
                Uses self-signed certificate. Your browser will show a security warning.
              </p>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={setupMutation.isPending}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {setupMutation.isPending ? "Configuring..." : "Configure SSL"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add web/src/routes/setup/ssl.tsx
git commit -m "feat: add SSL setup wizard page"
```

---

## Task 10: Add SSL Setup Redirect Logic

**Files:**
- Modify: `web/src/routes/__root.tsx` (or appropriate root layout)

**Step 1: Add SSL status check to root layout**

Add a check in the root layout that redirects to `/setup/ssl` if SSL is not configured and user is not already on that page.

```tsx
// In root layout or App component
const { data: sslStatus } = useQuery({
  queryKey: ["ssl-status"],
  queryFn: getSSLStatus,
  staleTime: Infinity, // Only check once per session
});

// Redirect to SSL setup if not configured
if (sslStatus && !sslStatus.ssl_configured && !location.pathname.startsWith("/setup/ssl")) {
  navigate({ to: "/setup/ssl" });
}
```

**Step 2: Commit**

```bash
git add web/src/routes/__root.tsx
git commit -m "feat: add SSL setup redirect logic"
```

---

## Task 11: Add Backend Tests

**Files:**
- Create: `api/tests/test_ssl_setup.py`

**Step 1: Write tests for SSL setup service and endpoints**

Create comprehensive tests for:
- `SSLSetupService` methods
- `/api/v1/setup/ssl-status` endpoint
- `/api/v1/setup/ssl` endpoint
- Certificate generation
- Traefik config generation

**Step 2: Run tests**

```bash
cd api && uv run pytest tests/test_ssl_setup.py -v
```

**Step 3: Commit**

```bash
git add api/tests/test_ssl_setup.py
git commit -m "test: add SSL setup tests"
```

---

## Task 12: Update Documentation

**Files:**
- Modify: `DEV_SETUP.md` or deployment docs

**Step 1: Document the SSL setup process**

Add section explaining:
- How the SSL setup wizard works
- Requirements for Let's Encrypt (domain, ports 80/443 open)
- Self-signed cert browser warnings
- How to re-run setup if needed

**Step 2: Commit**

```bash
git add DEV_SETUP.md
git commit -m "docs: add SSL setup documentation"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | SSLConfig database model | `models/ssl_config.py` |
| 2 | Pydantic schemas | `schemas/ssl_setup.py` |
| 3 | Certificate generator | `services/cert_generator.py` |
| 4 | Traefik config writer | `services/traefik_config.py` |
| 5 | SSL setup service | `services/ssl_setup_service.py` |
| 6 | SSL setup router | `routers/ssl_setup.py` |
| 7 | Docker Compose updates | `docker-compose.yml` |
| 8 | Frontend API client | `api/ssl-setup.ts` |
| 9 | SSL setup wizard page | `routes/setup/ssl.tsx` |
| 10 | SSL redirect logic | `routes/__root.tsx` |
| 11 | Backend tests | `tests/test_ssl_setup.py` |
| 12 | Documentation | `DEV_SETUP.md` |
