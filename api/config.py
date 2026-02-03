"""
Configuration management for HyperTrader API.

Uses pydantic-settings to load configuration from environment variables
with sensible defaults for development.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment Variables:
        DATABASE_URL: PostgreSQL connection string
        DEBUG: Enable debug mode (default: False)
        SECRET_KEY: Secret key for encryption/signing
        API_KEY_HEADER: Header name for API key authentication
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database configuration
    database_url: str = "postgresql://hypertrader:password@postgres:5432/hypertrader"

    # Application settings
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # JWT settings
    jwt_secret_key: str = "change-me-in-production-jwt-secret"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # API settings
    api_key_header: str = "X-API-Key"
    api_title: str = "HyperTrader API"
    api_version: str = "1.0.0"

    # Database pool settings
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = 3600  # Recycle connections after 1 hour

    # Encryption settings
    encryption_key: str = ""  # Fernet key for encrypting private keys

    # Kubernetes settings
    k8s_enabled: bool = True
    k8s_namespace: str = "hyper-trader"
    github_repo: str = "andreinasui/hyper-trader"
    templates_dir: str = "kubernetes/templates"
    reconciliation_interval: int = 30  # seconds


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings loaded from environment.
    """
    return Settings()
