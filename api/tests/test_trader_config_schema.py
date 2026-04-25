"""
Tests for trader configuration Pydantic schemas.

Covers:
- TraderConfigSchema: main configuration schema
- ProviderSettings: exchange, network, and account settings
- TradingStrategy: strategy type validation
- RiskParameters: risk management validation
- BucketConfig: order bucketing validation
- TraderConfigUpdateSchema: update-specific schema with optional self_account.address
"""

import pytest
from pydantic import ValidationError

from hyper_trader_api.schemas.trader_config import (
    AutoBucket,
    BucketConfig,
    CopyAccount,
    ManualBucket,
    ProviderSettings,
    RiskParameters,
    SelfAccount,
    TraderConfigSchema,
    TraderConfigUpdateSchema,
    TradingStrategy,
)


class TestTraderConfigSchema:
    """Tests for TraderConfigSchema - main configuration model."""

    def test_valid_minimal_config(self):
        """TraderConfigSchema accepts minimal valid configuration."""
        config_data = {
            "provider_settings": {
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

        config = TraderConfigSchema(**config_data)

        assert config.provider_settings.network == "mainnet"
        assert config.provider_settings.exchange == "hyperliquid"
        assert (
            config.provider_settings.self_account.address
            == "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"
        )
        assert config.provider_settings.self_account.is_sub is False
        assert (
            config.provider_settings.copy_account.address
            == "0x1234567890abcdef1234567890abcdef12345678"
        )
        assert config.trader_settings.min_self_funds == 100
        assert config.trader_settings.min_copy_funds == 1000
        assert config.trader_settings.trading_strategy.type == "order_based"

    def test_valid_full_config(self):
        """TraderConfigSchema accepts full configuration with all optional fields."""
        config_data = {
            "provider_settings": {
                "exchange": "hyperliquid",
                "network": "testnet",
                "self_account": {
                    "address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                    "is_sub": True,
                },
                "copy_account": {
                    "address": "0x1234567890abcdef1234567890abcdef12345678",
                },
                "slippage_bps": 50,
                "builder_fee_bps": 10,
            },
            "trader_settings": {
                "min_self_funds": 500,
                "min_copy_funds": 5000,
                "trading_strategy": {
                    "type": "order_based",
                    "risk_parameters": {
                        "allowed_assets": ["BTC", "ETH"],
                        "blocked_assets": ["DOGE"],
                        "max_leverage": 20,
                        "self_proportionality_multiplier": 2.5,
                    },
                    "bucket_config": {
                        "manual": {
                            "width_percent": 0.05,
                        },
                        "pricing_strategy": "aggressive",
                    },
                },
            },
        }

        config = TraderConfigSchema(**config_data)

        assert config.provider_settings.exchange == "hyperliquid"
        assert config.provider_settings.network == "testnet"
        assert config.provider_settings.self_account.is_sub is True
        assert config.provider_settings.slippage_bps == 50
        assert config.provider_settings.builder_fee_bps == 10
        assert config.trader_settings.min_self_funds == 500
        assert config.trader_settings.min_copy_funds == 5000
        assert config.trader_settings.trading_strategy.type == "order_based"
        assert config.trader_settings.trading_strategy.risk_parameters.max_leverage == 20
        assert (
            config.trader_settings.trading_strategy.risk_parameters.self_proportionality_multiplier
            == 2.5
        )
        assert (
            config.trader_settings.trading_strategy.bucket_config.pricing_strategy == "aggressive"
        )

    def test_min_funds_default_to_one(self):
        """TraderSettings min_self_funds and min_copy_funds default to 1."""
        from hyper_trader_api.schemas.trader_config import TraderSettings, TradingStrategy

        settings = TraderSettings(
            trading_strategy=TradingStrategy(type="order_based"),
        )
        assert settings.min_self_funds == 1
        assert settings.min_copy_funds == 1


class TestProviderSettingsValidation:
    """Tests for ProviderSettings validation rules."""

    def test_invalid_ethereum_address(self):
        """ProviderSettings rejects invalid Ethereum addresses."""
        # Missing 0x prefix
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="e221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
                copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
            )
        assert "address" in str(exc_info.value).lower()

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="0x1234"),
                copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
            )
        assert "address" in str(exc_info.value).lower()

        # Invalid characters
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="0xGGGGef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
                copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
            )
        assert "address" in str(exc_info.value).lower()

    def test_invalid_network(self):
        """ProviderSettings rejects invalid network values."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="devnet",  # Invalid - only mainnet or testnet allowed
                self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
                copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
            )
        assert "network" in str(exc_info.value).lower()

    def test_slippage_bps_default_is_200(self):
        """ProviderSettings slippage_bps defaults to 200 bps."""
        settings = ProviderSettings(
            network="mainnet",
            self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
            copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
        )
        assert settings.slippage_bps == 200

    def test_slippage_bps_bounds(self):
        """ProviderSettings validates slippage_bps is between 0 and 1000."""
        # Valid: 0
        settings = ProviderSettings(
            network="mainnet",
            self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
            copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
            slippage_bps=0,
        )
        assert settings.slippage_bps == 0

        # Valid: 1000
        settings = ProviderSettings(
            network="mainnet",
            self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
            copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
            slippage_bps=1000,
        )
        assert settings.slippage_bps == 1000

        # Invalid: negative
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
                copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
                slippage_bps=-1,
            )
        assert "slippage_bps" in str(exc_info.value).lower()

        # Invalid: too high
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
                copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
                slippage_bps=1001,
            )
        assert "slippage_bps" in str(exc_info.value).lower()

    def test_builder_fee_bps_bounds(self):
        """ProviderSettings validates builder_fee_bps is between 0 and 200."""
        # Valid: 0
        settings = ProviderSettings(
            network="mainnet",
            self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
            copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
            builder_fee_bps=0,
        )
        assert settings.builder_fee_bps == 0

        # Valid: 200
        settings = ProviderSettings(
            network="mainnet",
            self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
            copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
            builder_fee_bps=200,
        )
        assert settings.builder_fee_bps == 200

        # Invalid: negative
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
                copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
                builder_fee_bps=-1,
            )
        assert "builder_fee_bps" in str(exc_info.value).lower()

        # Invalid: too high
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
                copy_account=CopyAccount(address="0x1234567890abcdef1234567890abcdef12345678"),
                builder_fee_bps=201,
            )
        assert "builder_fee_bps" in str(exc_info.value).lower()


class TestTradingStrategyValidation:
    """Tests for TradingStrategy validation rules."""

    def test_invalid_strategy_type(self):
        """TradingStrategy rejects invalid strategy types."""
        with pytest.raises(ValidationError) as exc_info:
            TradingStrategy(type="invalid_strategy")
        assert "type" in str(exc_info.value).lower()

    def test_valid_order_based(self):
        """TradingStrategy accepts 'order_based' strategy type."""
        strategy = TradingStrategy(type="order_based")
        assert strategy.type == "order_based"
        assert strategy.risk_parameters is not None

    def test_position_based_rejected(self):
        """TradingStrategy rejects 'position_based' strategy type (only order_based allowed)."""
        with pytest.raises(ValidationError) as exc_info:
            TradingStrategy(type="position_based")
        assert "type" in str(exc_info.value).lower()


class TestRiskParametersValidation:
    """Tests for RiskParameters validation rules."""

    def test_max_leverage_bounds(self):
        """RiskParameters validates max_leverage is between 1 and 40."""
        # Valid: 1
        params = RiskParameters(max_leverage=1)
        assert params.max_leverage == 1

        # Valid: 40
        params = RiskParameters(max_leverage=40)
        assert params.max_leverage == 40

        # Valid: None (disabled)
        params = RiskParameters(max_leverage=None)
        assert params.max_leverage is None

        # Invalid: 0
        with pytest.raises(ValidationError) as exc_info:
            RiskParameters(max_leverage=0)
        assert "max_leverage" in str(exc_info.value).lower()

        # Invalid: 41
        with pytest.raises(ValidationError) as exc_info:
            RiskParameters(max_leverage=41)
        assert "max_leverage" in str(exc_info.value).lower()

    def test_self_proportionality_multiplier_bounds(self):
        """RiskParameters validates self_proportionality_multiplier is between 0.01 and 10.0."""
        # Valid: 0.01 (minimum)
        params = RiskParameters(self_proportionality_multiplier=0.01)
        assert params.self_proportionality_multiplier == 0.01

        # Valid: 10.0 (maximum)
        params = RiskParameters(self_proportionality_multiplier=10.0)
        assert params.self_proportionality_multiplier == 10.0

        # Valid: default is 1.0
        params = RiskParameters()
        assert params.self_proportionality_multiplier == 1.0

        # Invalid: 0.009 (too small)
        with pytest.raises(ValidationError) as exc_info:
            RiskParameters(self_proportionality_multiplier=0.009)
        assert "self_proportionality_multiplier" in str(exc_info.value).lower()

        # Invalid: 10.1 (too large)
        with pytest.raises(ValidationError) as exc_info:
            RiskParameters(self_proportionality_multiplier=10.1)
        assert "self_proportionality_multiplier" in str(exc_info.value).lower()


class TestBucketConfigValidation:
    """Tests for BucketConfig validation rules."""

    def test_manual_bucket_width_bounds(self):
        """BucketConfig validates manual bucket width_percent is between 0 and 1."""
        # Valid: 0.001 (just above 0)
        config = BucketConfig(manual=ManualBucket(width_percent=0.001))
        assert config.manual.width_percent == 0.001

        # Valid: 1.0 (maximum)
        config = BucketConfig(manual=ManualBucket(width_percent=1.0))
        assert config.manual.width_percent == 1.0

        # Invalid: 0 (must be > 0)
        with pytest.raises(ValidationError) as exc_info:
            BucketConfig(manual=ManualBucket(width_percent=0.0))
        assert "width_percent" in str(exc_info.value).lower()

        # Invalid: 1.1 (too large)
        with pytest.raises(ValidationError) as exc_info:
            BucketConfig(manual=ManualBucket(width_percent=1.1))
        assert "width_percent" in str(exc_info.value).lower()

    def test_auto_bucket_defaults(self):
        """BucketConfig auto bucket has correct default values."""
        config = BucketConfig(auto=AutoBucket())

        assert config.auto.ratio_threshold == 1000.0
        assert config.auto.wide_bucket_percent == 0.01
        assert config.auto.narrow_bucket_percent == 0.0001

    def test_pricing_strategy_values(self):
        """BucketConfig pricing_strategy accepts valid values."""
        # Valid: vwap (default)
        config = BucketConfig(manual=ManualBucket(width_percent=0.01))
        assert config.pricing_strategy == "vwap"

        # Valid: aggressive
        config = BucketConfig(
            manual=ManualBucket(width_percent=0.01),
            pricing_strategy="aggressive",
        )
        assert config.pricing_strategy == "aggressive"

        # Invalid: other values
        with pytest.raises(ValidationError) as exc_info:
            BucketConfig(
                manual=ManualBucket(width_percent=0.01),
                pricing_strategy="invalid",
            )
        assert "pricing_strategy" in str(exc_info.value).lower()


class TestTraderConfigUpdateSchema:
    """Tests for TraderConfigUpdateSchema - update-specific model."""

    def test_self_account_address_optional(self):
        """TraderConfigUpdateSchema allows self_account.address to be optional."""
        config_data = {
            "provider_settings": {
                "network": "mainnet",
                "self_account": {
                    "is_sub": False,
                    # address is omitted - should be auto-filled by service layer
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

        config = TraderConfigUpdateSchema(**config_data)

        # self_account.address should be None when not provided
        assert config.provider_settings.self_account.address is None
        assert config.provider_settings.self_account.is_sub is False

    def test_self_account_address_can_be_provided(self):
        """TraderConfigUpdateSchema allows self_account.address to be provided explicitly."""
        config_data = {
            "provider_settings": {
                "network": "mainnet",
                "self_account": {
                    "address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                    "is_sub": True,
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

        config = TraderConfigUpdateSchema(**config_data)

        assert (
            config.provider_settings.self_account.address
            == "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"
        )
        assert config.provider_settings.self_account.is_sub is True

    def test_self_account_defaults_to_empty_object(self):
        """TraderConfigUpdateSchema uses default factory for self_account."""
        config_data = {
            "provider_settings": {
                "network": "mainnet",
                "copy_account": {
                    "address": "0x1234567890abcdef1234567890abcdef12345678",
                },
                # self_account omitted entirely
            },
            "trader_settings": {
                "min_self_funds": 100,
                "min_copy_funds": 1000,
                "trading_strategy": {
                    "type": "order_based",
                },
            },
        }

        config = TraderConfigUpdateSchema(**config_data)

        # self_account should use defaults
        assert config.provider_settings.self_account.address is None
        assert config.provider_settings.self_account.is_sub is False
