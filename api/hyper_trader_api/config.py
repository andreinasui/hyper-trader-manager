"""
Configuration management for HyperTrader API.

Uses pydantic-settings to load configuration from environment variables.
Automatically loads environment-specific .env files:
  - ENVIRONMENT=development → .env.dev
  - ENVIRONMENT=staging → .env.staging
  - ENVIRONMENT=production → .env.prod
  - Or explicitly set ENV_FILE to override
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file() -> str:
    """Determine which .env file to load based on environment."""
    # First check if ENV_FILE is explicitly set
    if env_file := os.getenv("ENV_FILE"):
        return env_file

    # Otherwise, determine from ENVIRONMENT
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        return ".env.prod"
    elif environment == "staging":
        return ".env.staging"
    else:
        return ".env.dev"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Required in production:
        PRIVY_APP_ID: Privy application ID
        PRIVY_APP_SECRET: Privy API secret
    """

    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_parse_none_str="null",
    )

    # ==================== Environment ====================
    environment: Literal["development", "staging", "production"] = "development"

    # ==================== Privy Authentication ====================
    privy_app_id: str = ""
    privy_app_secret: str = ""
    privy_jwks_url: str = ""  # If empty, constructed from privy_app_id
    privy_jwks_cache_ttl: int = 3600  # Cache JWKS for 1 hour

    @field_validator("privy_app_id", "privy_app_secret")
    @classmethod
    def validate_privy_credentials(cls, v: str, info) -> str:
        """Require Privy credentials in non-development environments."""
        env = os.getenv("ENVIRONMENT", "development")
        if not v and env != "development":
            raise ValueError(f"{info.field_name} is required in {env} environment")
        return v

    @property
    def privy_jwks_endpoint(self) -> str:
        """Get JWKS URL - uses custom URL or constructs from app_id."""
        if self.privy_jwks_url:
            return self.privy_jwks_url
        return f"https://auth.privy.io/api/v1/apps/{self.privy_app_id}/jwks.json"

    # ==================== Database ====================
    database_url: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = 3600

    # ==================== Server ====================
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    debug: bool = False

    # ==================== Logging ====================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ==================== CORS ====================
    cors_origins: str = "http://localhost:3000"

    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins_to_list(cls, v: str) -> list[str]:
        """Parse comma-separated string to list."""
        if not v.strip():
            return []
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # ==================== Rate Limiting ====================
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100  # requests per window
    rate_limit_window: int = 60  # seconds

    # ==================== HTTP Client ====================
    http_timeout: float = 10.0

    # ==================== Kubernetes ====================
    k8s_enabled: bool = True
    k8s_namespace: str = "hyper-trader"
    github_repo: str = "andreinasui/hyper-trader"
    image_tag: str = "latest"  # Docker image tag for all trader pods
    templates_dir: str = "api/templates"
    reconciliation_interval: int = 30

    # ==================== API Metadata ====================
    api_title: str = "HyperTrader API"
    api_version: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
