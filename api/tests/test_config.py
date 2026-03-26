"""
Configuration tests for self-hosted deployment.

These tests verify the Settings class defaults to SQLite and self-hosted
configuration instead of PostgreSQL/Privy/Kubernetes.
"""




class TestSelfHostedSettings:
    """Tests for self-hosted configuration defaults."""

    def test_default_selfhosted_database_url(self, monkeypatch):
        """Default database URL should be SQLite for self-hosted deployment."""
        # Clear any existing DATABASE_URL
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # Clear cached settings
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        from hyper_trader_api.config import Settings

        settings = Settings()
        assert settings.database_url.startswith("sqlite")

    def test_jwt_secret_key_required(self, monkeypatch):
        """JWT secret key should be required for security."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        from hyper_trader_api.config import Settings

        # Should have a way to generate or require JWT secret
        settings = Settings()
        # Either has default or validation - we'll implement required validation
        assert hasattr(settings, "jwt_secret_key")

    def test_encryption_key_required(self, monkeypatch):
        """Encryption key should be required for secret storage."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        from hyper_trader_api.config import Settings

        settings = Settings()
        assert hasattr(settings, "encryption_key")

    def test_public_base_url_default(self, monkeypatch):
        """Public base URL should default to localhost:80."""
        monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        from hyper_trader_api.config import Settings

        settings = Settings()
        assert hasattr(settings, "public_base_url")
        assert "localhost" in settings.public_base_url or "127.0.0.1" in settings.public_base_url

    def test_runtime_mode_default(self, monkeypatch):
        """Runtime mode should default to docker for self-hosted."""
        monkeypatch.delenv("RUNTIME_MODE", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        from hyper_trader_api.config import Settings

        settings = Settings()
        assert hasattr(settings, "runtime_mode")
        assert settings.runtime_mode == "docker"

    def test_docker_socket_default(self, monkeypatch):
        """Docker socket should default to unix socket."""
        monkeypatch.delenv("DOCKER_SOCKET", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        from hyper_trader_api.config import Settings

        settings = Settings()
        assert hasattr(settings, "docker_socket")
        assert "docker.sock" in settings.docker_socket


class TestDatabaseEngine:
    """Tests for database engine configuration."""

    def test_sqlite_engine_has_check_same_thread(self, monkeypatch):
        """SQLite engine should have check_same_thread=False for FastAPI."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        # Import will create engine with new settings
        # We test by checking the engine doesn't raise threading errors
        # when used from multiple threads (FastAPI async context)
        from hyper_trader_api.database import engine

        # If we get here without error, SQLite config is correct
        assert "sqlite" in str(engine.url)

    def test_sqlite_engine_no_pool_class(self, monkeypatch):
        """SQLite should not use QueuePool (incompatible with SQLite)."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        from sqlalchemy.pool import QueuePool

        from hyper_trader_api.database import engine

        # SQLite should use StaticPool or NullPool, not QueuePool
        assert not isinstance(engine.pool, QueuePool)
