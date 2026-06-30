"""
Tests for TraderService business logic validation.

Covers:
- Config validation rules (_validate_config)
- Create trader validation (create_trader)
- Start trader state validation and retry logic (start_trader)
- Stop trader state validation (stop_trader)
- Update trader info validation (update_trader_info)
- Trader ownership validation (get_trader)
"""

import uuid
from datetime import UTC
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from hyper_trader_api.models.user import User
from hyper_trader_api.schemas.trader import TraderCreate, TraderInfoUpdate
from hyper_trader_api.schemas.trader_config import TraderConfigSchema
from hyper_trader_api.services.trader_service import (
    TraderNotFoundError,
    TraderOwnershipError,
    TraderService,
    TraderServiceError,
)


@pytest.fixture
def mock_runtime():
    """Mock Docker runtime."""
    runtime = MagicMock()
    runtime.create_secret.return_value = None
    runtime.create_service.return_value = None
    runtime.remove_service.return_value = None
    runtime.service_exists.return_value = False
    return runtime


@pytest.fixture
def trader_service(mock_db: Session, mock_runtime):
    """Create TraderService with mocked dependencies."""
    with patch(
        "hyper_trader_api.services.trader_service.get_runtime",
        return_value=mock_runtime,
    ):
        with patch("hyper_trader_api.services.trader_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.image_tag = "latest"
            mock_settings.return_value = settings

            service = TraderService(mock_db)
            yield service


@pytest.fixture
def valid_config():
    """Valid trader configuration dict."""
    return {
        "provider_settings": {
            "exchange": "hyperliquid",
            "network": "mainnet",
            "self_account": {
                "address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
            },
            "copy_account": {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
            },
            "risk_parameters": {
                "allowed_assets": "*",
            },
        },
        "trader_settings": {
            "trading_strategy": {
                "type": "position_based",
            },
        },
    }


class TestConfigValidation:
    """Tests for _validate_config method."""

    def test_copy_account_cannot_equal_self_account(self, trader_service: TraderService):
        """Test that copy account cannot be the same as self account."""
        wallet_address = "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"
        config = {
            "provider_settings": {
                "self_account": {"address": wallet_address},
                "copy_account": {"address": wallet_address},  # Same as self
            },
        }

        with pytest.raises(ValueError, match="Copy account cannot be the same as self account"):
            trader_service._validate_config(config, wallet_address)

    def test_copy_account_case_insensitive_comparison(self, trader_service: TraderService):
        """Test that address comparison is case-insensitive."""
        wallet_address = "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"
        config = {
            "provider_settings": {
                "self_account": {"address": wallet_address.lower()},
                "copy_account": {"address": wallet_address.upper()},  # Different case but same
            },
        }

        with pytest.raises(ValueError, match="Copy account cannot be the same as self account"):
            trader_service._validate_config(config, wallet_address)

    def test_allowed_and_blocked_assets_cannot_overlap(self, trader_service: TraderService):
        """Test that allowed and blocked asset lists cannot overlap."""
        config = {
            "provider_settings": {
                "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
                "copy_account": {"address": "0x1234567890abcdef1234567890abcdef12345678"},
                "risk_parameters": {
                    "allowed_assets": ["BTC", "ETH", "SOL"],
                    "blocked_assets": ["ETH", "DOGE"],  # ETH overlaps
                },
            },
            "trader_settings": {"trading_strategy": {"type": "position_based"}},
        }

        with pytest.raises(ValueError, match="Assets cannot be both allowed and blocked"):
            trader_service._validate_config(config, "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a")

    def test_allowed_assets_star_skips_overlap_check(self, trader_service: TraderService):
        """Test that '*' allowed_assets skips overlap check with blocked_assets."""
        config = {
            "provider_settings": {
                "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
                "copy_account": {"address": "0x1234567890abcdef1234567890abcdef12345678"},
                "risk_parameters": {
                    "allowed_assets": "*",
                    "blocked_assets": ["ETH"],
                },
            },
            "trader_settings": {"trading_strategy": {"type": "position_based"}},
        }
        # Should not raise — '*' + blocked is a valid combo
        trader_service._validate_config(config, "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a")

    def test_valid_config_passes_validation(
        self, trader_service: TraderService, valid_config: dict
    ):
        """Test that valid config passes all validation rules."""
        # Should not raise any exceptions
        trader_service._validate_config(valid_config, "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a")


class TestCreateTrader:
    """Tests for create_trader method."""

    def test_create_trader_rejects_duplicate_wallet(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        valid_config: dict,
    ):
        """Test that duplicate wallet addresses are rejected."""
        wallet_address = "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"

        # Mock existing trader with same wallet
        existing_trader = Mock()
        existing_trader.wallet_address = wallet_address.lower()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_trader

        trader_data = TraderCreate(
            wallet_address=wallet_address,
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            config=TraderConfigSchema(**valid_config),
        )

        with pytest.raises(ValueError, match="Trader already exists for wallet"):
            trader_service.create_trader(mock_user, trader_data)

    def test_create_trader_rejects_duplicate_name_for_user(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        valid_config: dict,
    ):
        """Test that duplicate names for same user are rejected."""

        # Mock: no existing trader with same wallet (first query)
        # Mock: existing trader with same name for same user (second query)
        def query_side_effect(*args):
            query_mock = Mock()
            # First call: check wallet - return None (no duplicate wallet)
            # Second call: check name - return existing trader (duplicate name)
            if not hasattr(query_side_effect, "call_count"):
                query_side_effect.call_count = 0
            query_side_effect.call_count += 1

            if query_side_effect.call_count == 1:
                # First query: check wallet address
                query_mock.filter.return_value.first.return_value = None
            else:
                # Second query: check name uniqueness
                existing_trader = Mock()
                existing_trader.name = "My Trader"
                query_mock.filter.return_value.first.return_value = existing_trader

            return query_mock

        mock_db.query.side_effect = query_side_effect

        trader_data = TraderCreate(
            wallet_address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            config=TraderConfigSchema(**valid_config),
            name="My Trader",
        )

        with pytest.raises(ValueError, match="A trader with name 'My Trader' already exists"):
            trader_service.create_trader(mock_user, trader_data)


class TestStartTrader:
    """Tests for start_trader method."""

    def test_start_trader_validates_startable_state(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Test that start only works from valid states (not 'running')."""
        trader_id = uuid.uuid4()

        # Mock trader in "running" state (not startable)
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        with pytest.raises(ValueError, match="Trader cannot be started from status 'running'"):
            trader_service.start_trader(trader_id, mock_user.id)

    def test_start_trader_accepts_configured_state(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that start works from 'configured' state."""
        trader_id = uuid.uuid4()

        # Mock trader in "configured" state
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "configured"
        trader.runtime_name = "trader-12345678"
        trader.start_attempts = 0
        trader.last_error = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        # Mock _get_config_data to return YAML string without DB lookup
        with patch.object(trader_service, "_get_config_data", return_value="{}"):
            result = trader_service.start_trader(trader_id, mock_user.id)

        # Verify trader status was updated to "running"
        assert trader.status == "running"
        assert result == trader
        mock_runtime.create_service.assert_called_once()

    def test_start_trader_retries_on_failure(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that start retries up to max_attempts and sets 'failed' status."""
        trader_id = uuid.uuid4()

        # Mock trader
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "configured"
        trader.runtime_name = "trader-12345678"
        trader.start_attempts = 0
        trader.last_error = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        # Mock runtime to always fail
        mock_runtime.create_service.side_effect = Exception("Docker error")

        # Mock _get_config_data to return YAML string without DB lookup
        with patch.object(trader_service, "_get_config_data", return_value="{}"):
            with patch("time.sleep"):  # Skip sleep delays in tests
                with pytest.raises(
                    TraderServiceError, match="Failed to start trader after 3 attempts"
                ):
                    trader_service.start_trader(trader_id, mock_user.id, max_attempts=3)

        # Verify trader status was set to "failed"
        assert trader.status == "failed"
        assert trader.last_error == "Docker error"
        assert trader.start_attempts == 3

    def test_start_trader_sets_last_started_at(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that start_trader stamps last_started_at and clears last_error on success."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "configured"
        trader.runtime_name = "trader-12345678"
        trader.start_attempts = 0
        trader.last_error = "previous error"
        trader.last_started_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        with patch.object(trader_service, "_get_config_data", return_value="{}"):
            result = trader_service.start_trader(trader_id, mock_user.id)

        assert result == trader
        assert trader.status == "running"
        assert trader.last_started_at is not None
        assert trader.last_error is None


class TestStopTrader:
    """Tests for stop_trader method."""

    def test_stop_trader_validates_stoppable_state(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Test that stop only works from valid states (not 'configured')."""
        trader_id = uuid.uuid4()

        # Mock trader in "configured" state (not stoppable)
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "configured"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        with pytest.raises(ValueError, match="Trader cannot be stopped from status 'configured'"):
            trader_service.stop_trader(trader_id, mock_user.id)

    def test_stop_trader_sets_stopping_and_returns_immediately(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Stop sets DB status to 'stopping', calls remove_service, does NOT set 'stopped'."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.stopped_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        mock_runtime.service_exists.return_value = True

        result = trader_service.stop_trader(trader_id, mock_user.id)

        assert trader.status == "stopping"
        assert trader.stopped_at is None
        assert result == trader
        mock_runtime.stop_service_and_capture_logs.assert_called_once_with(trader.runtime_name)
        mock_runtime.remove_service.assert_called_once_with(trader.runtime_name)

    def test_stop_trader_rejects_already_stopping(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Stop is a no-op-error when trader is already stopping."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "stopping"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        with pytest.raises(ValueError, match="Trader cannot be stopped from status 'stopping'"):
            trader_service.stop_trader(trader_id, mock_user.id)

    def test_stop_trader_stops_service_before_archive_and_remove(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """stop_trader lets the service shut down before archiving and removing it."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.stopped_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        mock_runtime.service_exists.return_value = True
        trader_service.archive_service = MagicMock()
        events = []
        mock_runtime.stop_service_and_capture_logs.side_effect = (
            lambda runtime_name: events.append("stop") or "boot\ncleanup\n"
        )
        trader_service.archive_service.archive_run.side_effect = (
            lambda trader_arg, logs=None: events.append(("archive", logs))
        )
        mock_runtime.remove_service.side_effect = lambda runtime_name: events.append("remove")

        trader_service.stop_trader(trader_id, mock_user.id)

        assert events == ["stop", ("archive", "boot\ncleanup\n"), "remove"]
        mock_runtime.stop_service_and_capture_logs.assert_called_once_with(trader.runtime_name)
        mock_runtime.remove_service.assert_called_once_with(trader.runtime_name)

    def test_stop_trader_succeeds_when_archiving_fails(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """stop_trader still removes service even if archiving raises."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.stopped_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        mock_runtime.service_exists.return_value = True

        mock_archive = MagicMock()
        mock_archive.archive_run.side_effect = Exception("disk full")
        trader_service.archive_service = mock_archive

        # Should not raise — archive failure is best-effort
        result = trader_service.stop_trader(trader_id, mock_user.id)

        assert result == trader
        mock_runtime.stop_service_and_capture_logs.assert_called_once_with(trader.runtime_name)
        mock_runtime.remove_service.assert_called_once_with(trader.runtime_name)


class TestDeleteTrader:
    """Tests for delete_trader."""

    def test_delete_trader_purges_archive_directory(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """delete_trader calls purge_trader after DB delete."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "stopped"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        mock_archive = MagicMock()
        trader_service.archive_service = mock_archive

        trader_service.delete_trader(trader_id, mock_user.id)

        mock_archive.purge_trader.assert_called_once_with(str(trader_id))


class TestUpdateTraderInfo:
    """Tests for update_trader_info method."""

    def test_update_name_checks_uniqueness(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Test that name update checks for uniqueness."""
        trader_id = uuid.uuid4()

        # Mock the trader being updated
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.name = "Old Name"
        trader.runtime_name = "trader-12345678"

        # Mock duplicate name check
        existing_trader = Mock()
        existing_trader.id = "different-id"
        existing_trader.name = "New Name"

        def query_side_effect(*args):
            query_mock = Mock()
            if not hasattr(query_side_effect, "call_count"):
                query_side_effect.call_count = 0
            query_side_effect.call_count += 1

            if query_side_effect.call_count == 1:
                # First query: get_trader - return the trader
                query_mock.filter.return_value.first.return_value = trader
            else:
                # Second query: check name uniqueness - return existing trader
                query_mock.filter.return_value.first.return_value = existing_trader

            return query_mock

        mock_db.query.side_effect = query_side_effect

        update_data = TraderInfoUpdate(name="New Name")

        with pytest.raises(ValueError, match="A trader with name 'New Name' already exists"):
            trader_service.update_trader_info(trader_id, mock_user.id, update_data)

    def test_update_description_only(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Test that updating only description works without name uniqueness check."""
        trader_id = uuid.uuid4()

        # Mock the trader being updated
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.name = "My Trader"
        trader.description = "Old description"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        update_data = TraderInfoUpdate(description="New description")

        result = trader_service.update_trader_info(trader_id, mock_user.id, update_data)

        # Verify description was updated
        assert trader.description == "New description"
        assert trader.name == "My Trader"  # Name unchanged
        assert result == trader


class TestTraderOwnership:
    """Tests for ownership validation."""

    def test_get_trader_validates_ownership(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Test that getting trader validates user ownership."""
        trader_id = uuid.uuid4()
        different_user_id = str(uuid.uuid4())

        # Mock trader owned by different user
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = different_user_id  # Different user
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        with pytest.raises(TraderOwnershipError, match="does not own trader"):
            trader_service.get_trader(trader_id, mock_user.id)

    def test_get_trader_not_found(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Test that getting non-existent trader raises NotFoundError."""
        trader_id = uuid.uuid4()

        # Mock no trader found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(TraderNotFoundError, match="Trader not found"):
            trader_service.get_trader(trader_id, mock_user.id)


class TestRestartTrader:
    """Tests for restart_trader method (stop + start with fresh config)."""

    def test_restart_stops_service_then_starts_with_fresh_config(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that restart removes service, then starts with fresh DB config."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.start_attempts = 0
        trader.last_error = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        # First call (restart check): True, second call (start_trader check): False
        mock_runtime.service_exists.side_effect = [True, False]
        trader_service.archive_service = MagicMock()
        events = []
        mock_runtime.stop_service_and_capture_logs.side_effect = (
            lambda runtime_name: events.append("stop") or "boot\ncleanup\n"
        )
        trader_service.archive_service.archive_run.side_effect = (
            lambda trader_arg, logs=None: events.append(("archive", logs))
        )
        mock_runtime.remove_service.side_effect = lambda runtime_name: events.append("remove")

        with patch.object(trader_service, "_get_config_data", return_value="{}"):
            result = trader_service.restart_trader(trader_id, mock_user.id)

        assert events == ["stop", ("archive", "boot\ncleanup\n"), "remove"]
        mock_runtime.stop_service_and_capture_logs.assert_called_once_with(trader.runtime_name)
        # Verify service was removed during stop phase
        mock_runtime.remove_service.assert_called_once_with("trader-12345678")
        # Verify new service was created (start_trader path)
        mock_runtime.create_service.assert_called_once()
        # Verify trader ended up running
        assert trader.status == "running"
        assert result == trader

    def test_restart_skips_remove_if_service_not_exists(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that restart handles missing service gracefully."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.start_attempts = 0
        trader.last_error = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        mock_runtime.service_exists.return_value = False

        with patch.object(trader_service, "_get_config_data", return_value="{}"):
            trader_service.restart_trader(trader_id, mock_user.id)

        # Service was not running, so remove_service should NOT be called
        mock_runtime.remove_service.assert_not_called()
        # But create_service should still be called (fresh start)
        mock_runtime.create_service.assert_called_once()
        assert trader.status == "running"

    def test_restart_raises_if_stop_fails(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that restart raises TraderServiceError if stop phase fails."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        mock_runtime.service_exists.return_value = True
        mock_runtime.remove_service.side_effect = Exception("Docker error")

        with pytest.raises(TraderServiceError, match="Restart failed during stop"):
            trader_service.restart_trader(trader_id, mock_user.id)

    def test_restart_sets_failed_if_start_fails(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that restart sets trader to failed if start phase fails after stop."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.start_attempts = 0
        trader.last_error = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        mock_runtime.service_exists.return_value = True
        mock_runtime.create_service.side_effect = Exception("Docker create error")

        with patch.object(trader_service, "_get_config_data", return_value="{}"):
            with patch("time.sleep"):
                with pytest.raises(TraderServiceError, match="Failed to start trader"):
                    trader_service.restart_trader(trader_id, mock_user.id)

        # Trader should be in failed state after start phase fails
        assert trader.status == "failed"


class TestUpdateImage:
    """Tests for update_image method."""

    def test_update_image_running_trader(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test updating image for a running trader pulls, updates service, and updates DB."""
        trader_id = uuid.uuid4()

        # Mock running trader
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.image_tag = "0.4.3"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        result = trader_service.update_image(trader_id, mock_user.id, "0.4.4")

        # Verify pull was called
        mock_runtime.pull_image.assert_called_once_with("0.4.4")
        # Verify service update was called for running trader
        mock_runtime.update_service_image.assert_called_once_with("trader-12345678", "0.4.4")
        # Verify DB was updated
        assert trader.image_tag == "0.4.4"
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_with(trader)
        assert result == trader

    def test_update_image_stopped_trader(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test updating image for a stopped trader pulls and updates DB but not service."""
        trader_id = uuid.uuid4()

        # Mock stopped trader
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "stopped"
        trader.runtime_name = "trader-12345678"
        trader.image_tag = "0.4.3"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        result = trader_service.update_image(trader_id, mock_user.id, "0.4.4")

        # Verify pull was called
        mock_runtime.pull_image.assert_called_once_with("0.4.4")
        # Verify service update was NOT called for stopped trader
        mock_runtime.update_service_image.assert_not_called()
        # Verify DB was updated
        assert trader.image_tag == "0.4.4"
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_with(trader)
        assert result == trader

    def test_update_image_configured_trader(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test updating image for a configured trader pulls and updates DB but not service."""
        trader_id = uuid.uuid4()

        # Mock configured trader
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "configured"
        trader.runtime_name = "trader-12345678"
        trader.image_tag = "0.4.3"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        result = trader_service.update_image(trader_id, mock_user.id, "0.4.4")

        # Verify pull was called
        mock_runtime.pull_image.assert_called_once_with("0.4.4")
        # Verify service update was NOT called for configured trader
        mock_runtime.update_service_image.assert_not_called()
        # Verify DB was updated
        assert trader.image_tag == "0.4.4"
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_with(trader)
        assert result == trader

    def test_update_image_failed_trader(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test updating image for a failed trader pulls and updates DB but not service."""
        trader_id = uuid.uuid4()

        # Mock failed trader
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "failed"
        trader.runtime_name = "trader-12345678"
        trader.image_tag = "0.4.3"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        result = trader_service.update_image(trader_id, mock_user.id, "0.4.4")

        # Verify pull was called
        mock_runtime.pull_image.assert_called_once_with("0.4.4")
        # Verify service update was NOT called for failed trader
        mock_runtime.update_service_image.assert_not_called()
        # Verify DB was updated
        assert trader.image_tag == "0.4.4"
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_with(trader)
        assert result == trader

    def test_update_image_pull_failure(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that pull failure raises TraderServiceError and DB is not updated."""
        trader_id = uuid.uuid4()

        # Mock trader
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.image_tag = "0.4.3"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        # Mock pull to fail
        mock_runtime.pull_image.side_effect = Exception("Image not found")

        with pytest.raises(TraderServiceError, match="Failed to pull image '0.4.4'"):
            trader_service.update_image(trader_id, mock_user.id, "0.4.4")

        # Verify pull was attempted
        mock_runtime.pull_image.assert_called_once_with("0.4.4")
        # Verify service update was NOT called
        mock_runtime.update_service_image.assert_not_called()
        # Verify DB was NOT updated
        assert trader.image_tag == "0.4.3"  # Still old tag
        mock_db.commit.assert_not_called()

    def test_update_image_service_update_failure(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that service update failure raises TraderServiceError."""
        trader_id = uuid.uuid4()

        # Mock running trader
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"
        trader.image_tag = "0.4.3"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        # Mock pull to succeed but service update to fail
        mock_runtime.update_service_image.side_effect = Exception("Service update failed")

        with pytest.raises(TraderServiceError, match="Failed to update service image"):
            trader_service.update_image(trader_id, mock_user.id, "0.4.4")

        # Verify pull was called
        mock_runtime.pull_image.assert_called_once_with("0.4.4")
        # Verify service update was attempted
        mock_runtime.update_service_image.assert_called_once_with("trader-12345678", "0.4.4")
        # Verify DB was NOT updated (due to exception)
        mock_db.commit.assert_not_called()

    def test_update_image_trader_not_found(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Test that updating image for non-existent trader raises TraderNotFoundError."""
        trader_id = uuid.uuid4()

        # Mock no trader found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(TraderNotFoundError, match="Trader not found"):
            trader_service.update_image(trader_id, mock_user.id, "0.4.4")

    def test_update_image_wrong_owner(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        """Test that updating image for trader with wrong owner raises TraderOwnershipError."""
        trader_id = uuid.uuid4()
        different_user_id = str(uuid.uuid4())

        # Mock trader owned by different user
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = different_user_id  # Different user
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        with pytest.raises(TraderOwnershipError, match="does not own trader"):
            trader_service.update_image(trader_id, mock_user.id, "0.4.4")


class TestGetTraderStatusReconciliation:
    """Tests for stopping→stopped reconciliation in get_trader_status."""

    def test_get_status_keeps_stopping_when_service_still_exists(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """While DB=stopping and swarm service still exists, status stays 'stopping'."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "stopping"
        trader.runtime_name = "trader-12345678"
        trader.wallet_address = "0x" + "a" * 40
        trader.stopped_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        mock_runtime.service_exists.return_value = True
        mock_runtime.get_status.return_value = {
            "state": "stopped",
            "running": False,
            "replicas": "0/1",
        }

        result = trader_service.get_trader_status(trader_id, mock_user.id)

        assert trader.status == "stopping"
        assert trader.stopped_at is None
        assert result["status"] == "stopping"

    def test_get_status_transitions_to_stopped_when_service_gone(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """When DB=stopping and swarm service is gone, transition to 'stopped'."""
        trader_id = uuid.uuid4()

        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "stopping"
        trader.runtime_name = "trader-12345678"
        trader.wallet_address = "0x" + "a" * 40
        trader.stopped_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = trader
        mock_runtime.service_exists.return_value = False
        mock_runtime.get_status.return_value = {
            "state": "not_found",
            "running": False,
        }

        result = trader_service.get_trader_status(trader_id, mock_user.id)

        assert trader.status == "stopped"
        assert trader.stopped_at is not None
        assert result["status"] == "stopped"


class TestStartRestartGuards:
    """Tests that start/restart reject 'stopping' state."""

    def test_start_trader_rejects_stopping(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        trader_id = uuid.uuid4()
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "stopping"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        with pytest.raises(ValueError, match="still stopping"):
            trader_service.start_trader(trader_id, mock_user.id)

    def test_restart_trader_rejects_stopping(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
    ):
        trader_id = uuid.uuid4()
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "stopping"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        with pytest.raises(ValueError, match="still stopping"):
            trader_service.restart_trader(trader_id, mock_user.id)


class TestGetTraderLogs:
    """Tests for get_trader_logs."""

    def test_get_trader_logs_returns_list_of_lines(self, trader_service: TraderService):
        """get_trader_logs should return log output split into a list of lines."""
        trader_service.runtime.get_logs.return_value = "line1\nline2\nline3"

        mock_trader = MagicMock()
        mock_trader.id = str(uuid.uuid4())
        mock_trader.user_id = "user-1"
        mock_trader.runtime_name = "trader-ab12cd34"

        trader_service.db.query.return_value.filter.return_value.first.return_value = mock_trader

        result = trader_service.get_trader_logs(mock_trader.id, mock_trader.user_id)

        assert isinstance(result, list)
        assert result == ["line1", "line2", "line3"]

    def test_get_trader_logs_empty_returns_empty_list(self, trader_service: TraderService):
        """get_trader_logs should return an empty list when there are no logs."""
        trader_service.runtime.get_logs.return_value = ""

        mock_trader = MagicMock()
        mock_trader.id = str(uuid.uuid4())
        mock_trader.user_id = "user-1"
        mock_trader.runtime_name = "trader-ab12cd34"

        trader_service.db.query.return_value.filter.return_value.first.return_value = mock_trader

        result = trader_service.get_trader_logs(mock_trader.id, mock_trader.user_id)

        assert result == []

    def test_get_trader_logs_passes_since_until_to_runtime(self, trader_service: TraderService):
        """get_trader_logs should pass since/until to the runtime."""
        from datetime import datetime

        trader_service.runtime.get_logs.return_value = "2026-05-03T10:00:00Z line1"

        mock_trader = MagicMock()
        mock_trader.id = str(uuid.uuid4())
        mock_trader.user_id = "user-1"
        mock_trader.runtime_name = "trader-ab12cd34"
        trader_service.db.query.return_value.filter.return_value.first.return_value = mock_trader

        since = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        until = datetime(2026, 5, 3, 11, 0, tzinfo=UTC)

        trader_service.get_trader_logs(
            mock_trader.id, mock_trader.user_id, since=since, until=until
        )

        trader_service.runtime.get_logs.assert_called_once_with(
            mock_trader.runtime_name,
            100,
            since=since,
            until=until,
        )

    def test_download_trader_logs_returns_raw_string(self, trader_service: TraderService):
        """download_trader_logs should return the full log string for the time range."""
        from datetime import datetime

        raw_log = "2026-05-03T10:00:00Z line1\n2026-05-03T10:01:00Z line2"
        trader_service.runtime.get_logs.return_value = raw_log

        mock_trader = MagicMock()
        mock_trader.id = str(uuid.uuid4())
        mock_trader.user_id = "user-1"
        mock_trader.runtime_name = "trader-ab12cd34"
        trader_service.db.query.return_value.filter.return_value.first.return_value = mock_trader

        since = datetime(2026, 5, 3, 9, 0, tzinfo=UTC)
        until = datetime(2026, 5, 3, 11, 0, tzinfo=UTC)

        result = trader_service.download_trader_logs(
            mock_trader.id, mock_trader.user_id, since, until
        )

        assert result == raw_log
        trader_service.runtime.get_logs.assert_called_once_with(
            mock_trader.runtime_name,
            since=since,
            until=until,
            all_lines=True,
        )
