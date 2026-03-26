"""
Tests for SQLAlchemy models with SQLite schema.

Covers:
- User model with username/password authentication
- Trader model with runtime_name (docker container) instead of k8s_name
- TraderConfig with JSON instead of JSONB
- TraderSecret model
- SessionToken model (if needed for v1)
- Bootstrap database creation
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hyper_trader_api.database import Base
from hyper_trader_api.db.bootstrap import bootstrap_database
from hyper_trader_api.models import Trader, TraderConfig, User
from hyper_trader_api.models.session_token import SessionToken
from hyper_trader_api.models.trader import TraderSecret


@pytest.fixture
def sqlite_engine():
    """Create a SQLite in-memory engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sqlite_session(sqlite_engine):
    """Create a session for testing."""
    SessionFactory = sessionmaker(bind=sqlite_engine)
    session = SessionFactory()
    yield session
    session.rollback()
    session.close()


class TestBootstrap:
    """Test database bootstrap functionality."""

    def test_bootstrap_creates_all_tables(self):
        """Bootstrap should create all required tables in SQLite."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Run bootstrap
        bootstrap_database(engine)

        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = {
            "users",
            "traders",
            "trader_configs",
            "trader_secrets",
            "session_tokens",
        }

        assert expected_tables.issubset(set(tables)), (
            f"Missing tables: {expected_tables - set(tables)}"
        )

        engine.dispose()


class TestUserModel:
    """Test User model with local authentication."""

    def test_user_creation(self, sqlite_session):
        """User can be created with username and password."""
        user = User(
            username="testuser",
            password_hash="hashed_password_here",
            is_admin=False,
        )
        sqlite_session.add(user)
        sqlite_session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.password_hash == "hashed_password_here"
        assert user.is_admin is False
        assert user.created_at is not None

    def test_user_username_is_unique(self, sqlite_session):
        """Username must be unique across users."""
        sqlite_session.add(User(username="admin", password_hash="x", is_admin=True))
        sqlite_session.commit()

        # Try to add duplicate username
        sqlite_session.add(User(username="admin", password_hash="y", is_admin=False))
        with pytest.raises(IntegrityError):
            sqlite_session.commit()

    def test_user_admin_flag(self, sqlite_session):
        """Admin flag should work correctly."""
        admin = User(username="admin", password_hash="hash", is_admin=True)
        regular = User(username="user", password_hash="hash", is_admin=False)

        sqlite_session.add_all([admin, regular])
        sqlite_session.commit()

        assert admin.is_admin is True
        assert regular.is_admin is False


class TestTraderModel:
    """Test Trader model with SQLite-compatible types."""

    def test_trader_creation(self, sqlite_session):
        """Trader can be created with String ID instead of UUID."""
        user = User(username="trader_owner", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        trader = Trader(
            user_id=user.id,
            wallet_address="0x1234567890123456789012345678901234567890",
            runtime_name="trader-abc123",
            status="pending",
            image_tag="latest",
        )
        sqlite_session.add(trader)
        sqlite_session.commit()

        assert trader.id is not None
        assert isinstance(trader.id, str)  # String ID, not UUID object
        assert trader.runtime_name == "trader-abc123"
        assert trader.wallet_address == "0x1234567890123456789012345678901234567890"

    def test_trader_runtime_name_is_unique(self, sqlite_session):
        """runtime_name (docker container name) must be unique."""
        user = User(username="owner", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        trader1 = Trader(
            user_id=user.id,
            wallet_address="0x1111111111111111111111111111111111111111",
            runtime_name="trader-container-1",
            status="running",
        )
        sqlite_session.add(trader1)
        sqlite_session.commit()

        # Try to add duplicate runtime_name
        trader2 = Trader(
            user_id=user.id,
            wallet_address="0x2222222222222222222222222222222222222222",
            runtime_name="trader-container-1",  # Same name
            status="running",
        )
        sqlite_session.add(trader2)
        with pytest.raises(IntegrityError):
            sqlite_session.commit()

    def test_trader_cascade_delete(self, sqlite_session):
        """Deleting user should cascade delete traders."""
        user = User(username="cascade_test", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        trader = Trader(
            user_id=user.id,
            wallet_address="0x3333333333333333333333333333333333333333",
            runtime_name="trader-cascade",
        )
        sqlite_session.add(trader)
        sqlite_session.commit()

        trader_id = trader.id

        # Delete user
        sqlite_session.delete(user)
        sqlite_session.commit()

        # Trader should be gone
        assert sqlite_session.get(Trader, trader_id) is None


class TestTraderConfigModel:
    """Test TraderConfig with JSON instead of JSONB."""

    def test_config_uses_json_not_jsonb(self, sqlite_session):
        """TraderConfig should use JSON type, compatible with SQLite."""
        user = User(username="config_user", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        trader = Trader(
            user_id=user.id,
            wallet_address="0x4444444444444444444444444444444444444444",
            runtime_name="trader-config-test",
        )
        sqlite_session.add(trader)
        sqlite_session.commit()

        config = TraderConfig(
            trader_id=trader.id,
            config_json={
                "name": "Test Config",
                "exchange": "hyperliquid",
                "strategies": ["momentum", "arbitrage"],
                "max_position_size": 1000.50,
            },
            version=1,
        )
        sqlite_session.add(config)
        sqlite_session.commit()

        # Retrieve and verify JSON is preserved
        retrieved = sqlite_session.get(TraderConfig, config.id)
        assert retrieved.config_json["name"] == "Test Config"
        assert retrieved.config_json["exchange"] == "hyperliquid"
        assert retrieved.config_json["strategies"] == ["momentum", "arbitrage"]
        assert retrieved.config_json["max_position_size"] == 1000.50

    def test_config_version_constraint(self, sqlite_session):
        """Trader config version should be unique per trader."""
        user = User(username="version_user", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        trader = Trader(
            user_id=user.id,
            wallet_address="0x5555555555555555555555555555555555555555",
            runtime_name="trader-version-test",
        )
        sqlite_session.add(trader)
        sqlite_session.commit()

        config1 = TraderConfig(
            trader_id=trader.id,
            config_json={"version": "v1"},
            version=1,
        )
        sqlite_session.add(config1)
        sqlite_session.commit()

        # Try to add duplicate version
        config2 = TraderConfig(
            trader_id=trader.id,
            config_json={"version": "v1-duplicate"},
            version=1,  # Same version
        )
        sqlite_session.add(config2)
        with pytest.raises(IntegrityError):
            sqlite_session.commit()


class TestTraderSecretModel:
    """Test TraderSecret model."""

    def test_secret_creation(self, sqlite_session):
        """TraderSecret can be created and linked to trader."""
        user = User(username="secret_user", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        trader = Trader(
            user_id=user.id,
            wallet_address="0x6666666666666666666666666666666666666666",
            runtime_name="trader-secret-test",
        )
        sqlite_session.add(trader)
        sqlite_session.commit()

        secret = TraderSecret(
            trader_id=trader.id,
            private_key_encrypted="encrypted_private_key_data",
        )
        sqlite_session.add(secret)
        sqlite_session.commit()

        assert secret.id is not None
        assert secret.trader_id == trader.id
        assert secret.private_key_encrypted == "encrypted_private_key_data"

    def test_secret_one_per_trader(self, sqlite_session):
        """Each trader should have only one secret."""
        user = User(username="one_secret_user", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        trader = Trader(
            user_id=user.id,
            wallet_address="0x7777777777777777777777777777777777777777",
            runtime_name="trader-one-secret",
        )
        sqlite_session.add(trader)
        sqlite_session.commit()

        secret1 = TraderSecret(
            trader_id=trader.id,
            private_key_encrypted="secret1",
        )
        sqlite_session.add(secret1)
        sqlite_session.commit()

        # Try to add another secret for same trader
        secret2 = TraderSecret(
            trader_id=trader.id,
            private_key_encrypted="secret2",
        )
        sqlite_session.add(secret2)
        with pytest.raises(IntegrityError):
            sqlite_session.commit()


class TestSessionTokenModel:
    """Test SessionToken model for token revocation."""

    def test_token_creation(self, sqlite_session):
        """SessionToken can be created for user sessions."""
        user = User(username="token_user", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        token = SessionToken(
            user_id=user.id,
            token_hash="hashed_token_value",
            expires_at=datetime.now(UTC),
            is_revoked=False,
        )
        sqlite_session.add(token)
        sqlite_session.commit()

        assert token.id is not None
        assert token.user_id == user.id
        assert token.token_hash == "hashed_token_value"
        assert token.is_revoked is False

    def test_token_revocation(self, sqlite_session):
        """Token can be revoked."""
        user = User(username="revoke_user", password_hash="hash", is_admin=False)
        sqlite_session.add(user)
        sqlite_session.commit()

        token = SessionToken(
            user_id=user.id,
            token_hash="token_to_revoke",
            expires_at=datetime.now(UTC),
            is_revoked=False,
        )
        sqlite_session.add(token)
        sqlite_session.commit()

        # Revoke token
        token.is_revoked = True
        sqlite_session.commit()

        retrieved = sqlite_session.get(SessionToken, token.id)
        assert retrieved.is_revoked is True
