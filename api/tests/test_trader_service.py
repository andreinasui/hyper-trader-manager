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
    with patch("hyper_trader_api.services.trader_service.get_runtime", return_value=mock_runtime):
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
        },
        "trader_settings": {
            "min_self_funds": 100,
            "min_copy_funds": 1000,
            "trading_strategy": {
                "type": "order_based",
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
            },
            "trader_settings": {
                "trading_strategy": {
                    "risk_parameters": {
                        "allowed_assets": ["BTC", "ETH", "SOL"],
                        "blocked_assets": ["ETH", "DOGE"],  # ETH overlaps
                    }
                }
            },
        }

        with pytest.raises(ValueError, match="Assets cannot be both allowed and blocked"):
            trader_service._validate_config(config, "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a")

    def test_bucket_config_cannot_have_both_manual_and_auto(self, trader_service: TraderService):
        """Test that bucket config cannot have both manual and auto."""
        config = {
            "provider_settings": {
                "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
                "copy_account": {"address": "0x1234567890abcdef1234567890abcdef12345678"},
            },
            "trader_settings": {
                "trading_strategy": {
                    "bucket_config": {
                        "manual": [{"size": 100}],
                        "auto": {"initial_size": 100},  # Both manual and auto
                    }
                }
            },
        }

        with pytest.raises(ValueError, match="Bucket config must use either manual or auto"):
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
        with patch.object(trader_service, "_get_config_data", return_value="provider_settings: {}"):
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
        with patch.object(trader_service, "_get_config_data", return_value="provider_settings: {}"):
            with patch("time.sleep"):  # Skip sleep delays in tests
                with pytest.raises(
                    TraderServiceError, match="Failed to start trader after 3 attempts"
                ):
                    trader_service.start_trader(trader_id, mock_user.id, max_attempts=3)

        # Verify trader status was set to "failed"
        assert trader.status == "failed"
        assert trader.last_error == "Docker error"
        assert trader.start_attempts == 3


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

    def test_stop_trader_from_running_state(
        self,
        mock_db: Session,
        mock_user: User,
        trader_service: TraderService,
        mock_runtime,
    ):
        """Test that stopping a running trader works."""
        trader_id = uuid.uuid4()

        # Mock trader in "running" state
        trader = Mock()
        trader.id = str(trader_id)
        trader.user_id = mock_user.id
        trader.status = "running"
        trader.runtime_name = "trader-12345678"

        mock_db.query.return_value.filter.return_value.first.return_value = trader

        # Mock service exists to return True (service is running)
        mock_runtime.service_exists.return_value = True

        result = trader_service.stop_trader(trader_id, mock_user.id)

        # Verify trader status was updated to "stopped"
        assert trader.status == "stopped"
        assert result == trader
        mock_runtime.remove_service.assert_called_once_with(trader.runtime_name)


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

        with patch.object(trader_service, "_get_config_data", return_value="provider_settings: {}"):
            result = trader_service.restart_trader(trader_id, mock_user.id)

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

        with patch.object(trader_service, "_get_config_data", return_value="provider_settings: {}"):
            result = trader_service.restart_trader(trader_id, mock_user.id)

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

        with patch.object(trader_service, "_get_config_data", return_value="provider_settings: {}"):
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
