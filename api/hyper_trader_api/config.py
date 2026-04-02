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
    """

    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_parse_none_str="null",
    )

    # ==================== Environment ====================
    environment: Literal["development", "production"] = "development"

    # ==================== Database ====================
    database_url: str = "sqlite:///./data/hypertrader.db"

    # ==================== Self-Hosted Configuration ====================
    public_base_url: str = "http://localhost:80"
    public_port: int = 80
    docker_socket: str = "unix:///var/run/docker.sock"
    runtime_mode: Literal["docker"] = "docker"
    image_tag: str = "latest"  # Docker image tag for trader containers
    data_dir: str = "./data"  # Base directory for app data (traefik config, certs, etc.)

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

    # ==================== API Metadata ====================
    api_title: str = "HyperTrader API"
    api_version: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
