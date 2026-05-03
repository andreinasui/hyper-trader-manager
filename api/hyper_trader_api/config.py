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
from importlib.metadata import version as get_package_version
from typing import Literal

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file() -> str:
    if env_file := os.getenv("ENV_FILE"):
        return env_file


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

    # Optional ACME CA server URL (e.g. Pebble for local testing).
    # When None (default) Traefik uses Let's Encrypt production directly.
    # When set, Traefik's ACME resolver points here instead. Used for local
    # SSL testing without hitting real Let's Encrypt rate limits.
    acme_ca_server: str | None = None

    # ==================== Database ====================
    database_url: str = "sqlite:///./data/hypertrader.db"

    # ==================== Self-Hosted Configuration ====================
    data_dir: str = "./data"  # Base directory for app data (traefik config, certs, etc.)
    traefik_config_dir: str = (
        "/host-traefik"  # Path to Traefik config directory (bind-mounted from host)
    )

    # ==================== Update System ====================
    github_repo: str = "andreinasui/hyper-trader-manager"
    update_state_dir: str = "/var/lib/update-state"
    compose_project_dir: str | None = None  # None disables the update system (e.g. in dev)
    update_check_interval_hours: int = 24
    update_health_check_timeout_seconds: int = 60
    helper_image: str = "ghcr.io/andreinasui/hyper-trader-manager-update-helper:latest"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def debug(self) -> str:
        return self.environment == "development"

    # ==================== Logging ====================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ==================== CORS ====================
    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return ["http://localhost"]

    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins_to_list(cls, v: str) -> list[str]:
        """Parse comma-separated string to list."""
        if not v.strip():
            return []
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # ==================== API Metadata ====================
    @computed_field  # type: ignore[prop-decorator]
    @property
    def api_title(self) -> str:
        return "HyperTrader API"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def api_version(self) -> str:
        """Version derived from pyproject.toml; appends -dev in development."""
        base = get_package_version("hyper-trader-api")
        return f"{base}-dev" if self.environment == "development" else base


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
