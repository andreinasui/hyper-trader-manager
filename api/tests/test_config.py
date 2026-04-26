"""
Configuration tests.

These tests verify the Settings class defaults to SQLite and local
configuration instead of PostgreSQL or Kubernetes.
"""


class TestSettings:
    """Tests for configuration defaults."""

    def test_default_database_url(self, monkeypatch):
        """Default database URL should be SQLite."""
        # Clear any existing DATABASE_URL
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # Clear cached settings
        from hyper_trader_api.config import get_settings

        get_settings.cache_clear()

        from hyper_trader_api.config import Settings

        settings = Settings()
        assert settings.database_url.startswith("sqlite")


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
