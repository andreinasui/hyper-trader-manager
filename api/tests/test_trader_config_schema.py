"""
Tests for trader configuration Pydantic schemas.

Covers:
- TraderConfigSchema: main configuration schema
- ProviderSettings: exchange, network, and account settings
- ProviderRiskParameters: provider-level risk validation
- TradingStrategy: position_based and order_based validation
- OrderBasedRiskParameters: order-based risk parameters
- AutoBucketConfig / ManualBucketConfig: bucket config validation
- TraderConfigUpdateSchema: update-specific schema with optional self_account.address
"""

import pytest
from pydantic import ValidationError

from hyper_trader_api.schemas.trader_config import (
    AutoBucketConfig,
    CopyAccount,
    ManualBucketConfig,
    OrderBasedRiskParameters,
    OrderBasedStrategy,
    PositionBasedStrategy,
    ProviderRiskParameters,
    ProviderSettings,
    SelfAccount,
    TraderConfigSchema,
    TraderConfigUpdateSchema,
    TraderSettings,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

SELF_ADDR = "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"
COPY_ADDR = "0x1234567890abcdef1234567890abcdef12345678"

MINIMAL_PROVIDER = {
    "network": "mainnet",
    "self_account": {"address": SELF_ADDR},
    "copy_account": {"address": COPY_ADDR},
    "risk_parameters": {"allowed_assets": "*"},
}


class TestTraderConfigSchema:
    """Tests for TraderConfigSchema - main configuration model."""

    def test_valid_minimal_position_based(self):
        """TraderConfigSchema accepts minimal position_based configuration."""
        config = TraderConfigSchema(
            provider_settings=MINIMAL_PROVIDER,
            trader_settings={"trading_strategy": {"type": "position_based"}},
        )
        assert config.provider_settings.network == "mainnet"
        assert config.provider_settings.exchange == "hyperliquid"
        assert config.provider_settings.self_account.address == SELF_ADDR
        assert config.provider_settings.self_account.is_sub is False
        assert config.provider_settings.copy_account.address == COPY_ADDR
        assert config.trader_settings.trading_strategy.type == "position_based"

    def test_valid_minimal_order_based(self):
        """TraderConfigSchema accepts minimal order_based with auto bucket."""
        config = TraderConfigSchema(
            provider_settings=MINIMAL_PROVIDER,
            trader_settings={
                "trading_strategy": {
                    "type": "order_based",
                    "bucket_config": {"type": "auto"},
                }
            },
        )
        assert config.trader_settings.trading_strategy.type == "order_based"

    def test_valid_full_config(self):
        """TraderConfigSchema accepts full configuration with all optional fields."""
        config_data = {
            "provider_settings": {
                "exchange": "hyperliquid",
                "network": "testnet",
                "self_account": {"address": SELF_ADDR, "is_sub": True},
                "copy_account": {"address": COPY_ADDR},
                "slippage_bps": 50,
                "risk_parameters": {
                    "allowed_assets": ["BTC", "ETH"],
                    "blocked_assets": ["DOGE"],
                    "max_leverage": 20,
                },
            },
            "trader_settings": {
                "trading_strategy": {
                    "type": "order_based",
                    "risk_parameters": {
                        "self_proportionality_multiplier": 2.5,
                        "open_on_low_pnl": {"enabled": True, "max_pnl": 0.1},
                    },
                    "bucket_config": {
                        "type": "manual",
                        "width_percent": 0.05,
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
        assert config.provider_settings.risk_parameters.allowed_assets == ["BTC", "ETH"]
        assert config.provider_settings.risk_parameters.max_leverage == 20

        strategy = config.trader_settings.trading_strategy
        assert strategy.type == "order_based"
        assert strategy.risk_parameters.self_proportionality_multiplier == 2.5
        assert strategy.bucket_config.type == "manual"
        assert strategy.bucket_config.pricing_strategy == "aggressive"

    def test_extra_fields_rejected(self):
        """TraderConfigSchema rejects unknown top-level fields."""
        with pytest.raises(ValidationError):
            TraderConfigSchema(
                provider_settings=MINIMAL_PROVIDER,
                trader_settings={"trading_strategy": {"type": "position_based"}},
                unknown_field="bad",
            )


class TestProviderSettingsValidation:
    """Tests for ProviderSettings validation rules."""

    def test_invalid_ethereum_address(self):
        """ProviderSettings rejects invalid Ethereum addresses."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="e221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"),
                copy_account=CopyAccount(address=COPY_ADDR),
                risk_parameters=ProviderRiskParameters(allowed_assets="*"),
            )
        assert "address" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address="0x1234"),
                copy_account=CopyAccount(address=COPY_ADDR),
                risk_parameters=ProviderRiskParameters(allowed_assets="*"),
            )
        assert "address" in str(exc_info.value).lower()

    def test_invalid_network(self):
        """ProviderSettings rejects invalid network values."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="devnet",
                self_account=SelfAccount(address=SELF_ADDR),
                copy_account=CopyAccount(address=COPY_ADDR),
                risk_parameters=ProviderRiskParameters(allowed_assets="*"),
            )
        assert "network" in str(exc_info.value).lower()

    def test_slippage_bps_default_is_200(self):
        """ProviderSettings slippage_bps defaults to 200 bps."""
        settings = ProviderSettings(
            network="mainnet",
            self_account=SelfAccount(address=SELF_ADDR),
            copy_account=CopyAccount(address=COPY_ADDR),
            risk_parameters=ProviderRiskParameters(allowed_assets="*"),
        )
        assert settings.slippage_bps == 200

    def test_slippage_bps_bounds(self):
        """ProviderSettings validates slippage_bps is between 0 and 1000."""
        rp = ProviderRiskParameters(allowed_assets="*")

        settings = ProviderSettings(
            network="mainnet",
            self_account=SelfAccount(address=SELF_ADDR),
            copy_account=CopyAccount(address=COPY_ADDR),
            risk_parameters=rp,
            slippage_bps=0,
        )
        assert settings.slippage_bps == 0

        settings = ProviderSettings(
            network="mainnet",
            self_account=SelfAccount(address=SELF_ADDR),
            copy_account=CopyAccount(address=COPY_ADDR),
            risk_parameters=rp,
            slippage_bps=1000,
        )
        assert settings.slippage_bps == 1000

        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address=SELF_ADDR),
                copy_account=CopyAccount(address=COPY_ADDR),
                risk_parameters=rp,
                slippage_bps=-1,
            )
        assert "slippage_bps" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address=SELF_ADDR),
                copy_account=CopyAccount(address=COPY_ADDR),
                risk_parameters=rp,
                slippage_bps=1001,
            )
        assert "slippage_bps" in str(exc_info.value).lower()

    def test_risk_parameters_required(self):
        """ProviderSettings requires risk_parameters."""
        with pytest.raises(ValidationError):
            ProviderSettings(
                network="mainnet",
                self_account=SelfAccount(address=SELF_ADDR),
                copy_account=CopyAccount(address=COPY_ADDR),
            )


class TestProviderRiskParametersValidation:
    """Tests for ProviderRiskParameters validation rules."""

    def test_allowed_assets_star(self):
        """ProviderRiskParameters accepts '*' for all assets."""
        rp = ProviderRiskParameters(allowed_assets="*")
        assert rp.allowed_assets == "*"

    def test_allowed_assets_non_empty_list(self):
        """ProviderRiskParameters accepts non-empty list of assets."""
        rp = ProviderRiskParameters(allowed_assets=["BTC", "ETH"])
        assert rp.allowed_assets == ["BTC", "ETH"]

    def test_allowed_assets_empty_list_rejected(self):
        """ProviderRiskParameters rejects empty list for allowed_assets."""
        with pytest.raises(ValidationError):
            ProviderRiskParameters(allowed_assets=[])

    def test_blocked_assets_defaults_to_empty(self):
        """ProviderRiskParameters blocked_assets defaults to empty list."""
        rp = ProviderRiskParameters(allowed_assets="*")
        assert rp.blocked_assets == []

    def test_max_leverage_bounds(self):
        """ProviderRiskParameters validates max_leverage is between 1 and 50 or null."""
        assert ProviderRiskParameters(allowed_assets="*", max_leverage=1).max_leverage == 1
        assert ProviderRiskParameters(allowed_assets="*", max_leverage=50).max_leverage == 50
        assert ProviderRiskParameters(allowed_assets="*", max_leverage=None).max_leverage is None

        with pytest.raises(ValidationError) as exc_info:
            ProviderRiskParameters(allowed_assets="*", max_leverage=0)
        assert "max_leverage" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            ProviderRiskParameters(allowed_assets="*", max_leverage=51)
        assert "max_leverage" in str(exc_info.value).lower()


class TestTradingStrategyValidation:
    """Tests for TradingStrategy validation rules."""

    def test_invalid_strategy_type(self):
        """TraderSettings rejects invalid strategy types."""
        with pytest.raises(ValidationError):
            TraderSettings(trading_strategy={"type": "invalid_strategy"})

    def test_valid_position_based(self):
        """position_based strategy has only type."""
        strategy = PositionBasedStrategy(type="position_based")
        assert strategy.type == "position_based"

    def test_position_based_rejects_extra_fields(self):
        """position_based strategy rejects extra fields."""
        with pytest.raises(ValidationError):
            PositionBasedStrategy(type="position_based", bucket_config={"type": "auto"})

    def test_valid_order_based_with_auto_bucket(self):
        """order_based strategy requires bucket_config."""
        strategy = OrderBasedStrategy(
            type="order_based",
            bucket_config={"type": "auto"},
        )
        assert strategy.type == "order_based"
        assert strategy.bucket_config.type == "auto"

    def test_order_based_requires_bucket_config(self):
        """order_based strategy without bucket_config is invalid."""
        with pytest.raises(ValidationError):
            OrderBasedStrategy(type="order_based")


class TestOrderBasedRiskParametersValidation:
    """Tests for OrderBasedRiskParameters validation rules."""

    def test_defaults(self):
        """OrderBasedRiskParameters has correct defaults."""
        rp = OrderBasedRiskParameters()
        assert rp.self_proportionality_multiplier == 1.0
        assert rp.open_on_low_pnl.enabled is False
        assert rp.open_on_low_pnl.max_pnl == 0.0

    def test_self_proportionality_multiplier_must_be_positive(self):
        """self_proportionality_multiplier must be > 0."""
        assert OrderBasedRiskParameters(self_proportionality_multiplier=0.001).self_proportionality_multiplier == 0.001
        assert OrderBasedRiskParameters(self_proportionality_multiplier=100.0).self_proportionality_multiplier == 100.0

        with pytest.raises(ValidationError) as exc_info:
            OrderBasedRiskParameters(self_proportionality_multiplier=0.0)
        assert "self_proportionality_multiplier" in str(exc_info.value).lower()

    def test_open_on_low_pnl_max_pnl_bounds(self):
        """open_on_low_pnl.max_pnl must be between 0 and 1."""
        rp = OrderBasedRiskParameters(open_on_low_pnl={"enabled": True, "max_pnl": 1.0})
        assert rp.open_on_low_pnl.max_pnl == 1.0

        with pytest.raises(ValidationError):
            OrderBasedRiskParameters(open_on_low_pnl={"max_pnl": -0.1})

        with pytest.raises(ValidationError):
            OrderBasedRiskParameters(open_on_low_pnl={"max_pnl": 1.1})


class TestBucketConfigValidation:
    """Tests for AutoBucketConfig and ManualBucketConfig validation rules."""

    def test_auto_bucket_defaults(self):
        """AutoBucketConfig has correct default values."""
        bucket = AutoBucketConfig(type="auto")
        assert bucket.ratio_threshold == 1000.0
        assert bucket.wide_bucket_percent == 0.01
        assert bucket.narrow_bucket_percent == 0.0001
        assert bucket.pricing_strategy == "vwap"

    def test_auto_bucket_wide_percent_bounds(self):
        """wide_bucket_percent must be (0, 0.01]."""
        assert AutoBucketConfig(type="auto", wide_bucket_percent=0.005).wide_bucket_percent == 0.005

        with pytest.raises(ValidationError):
            AutoBucketConfig(type="auto", wide_bucket_percent=0.0)

        with pytest.raises(ValidationError):
            AutoBucketConfig(type="auto", wide_bucket_percent=0.011)

    def test_auto_bucket_narrow_percent_bounds(self):
        """narrow_bucket_percent must be [0, 0.01]."""
        assert AutoBucketConfig(type="auto", narrow_bucket_percent=0.0).narrow_bucket_percent == 0.0
        assert AutoBucketConfig(type="auto", narrow_bucket_percent=0.01).narrow_bucket_percent == 0.01

        with pytest.raises(ValidationError):
            AutoBucketConfig(type="auto", narrow_bucket_percent=0.011)

    def test_manual_bucket_width_bounds(self):
        """ManualBucketConfig validates width_percent is in [0, 1]."""
        assert ManualBucketConfig(type="manual", width_percent=0.0).width_percent == 0.0
        assert ManualBucketConfig(type="manual", width_percent=1.0).width_percent == 1.0

        with pytest.raises(ValidationError) as exc_info:
            ManualBucketConfig(type="manual", width_percent=1.1)
        assert "width_percent" in str(exc_info.value).lower()

    def test_pricing_strategy_values(self):
        """Bucket configs accept valid pricing_strategy values."""
        auto = AutoBucketConfig(type="auto", pricing_strategy="aggressive")
        assert auto.pricing_strategy == "aggressive"

        manual = ManualBucketConfig(type="manual", width_percent=0.01, pricing_strategy="vwap")
        assert manual.pricing_strategy == "vwap"

        with pytest.raises(ValidationError) as exc_info:
            ManualBucketConfig(type="manual", width_percent=0.01, pricing_strategy="invalid")
        assert "pricing_strategy" in str(exc_info.value).lower()

    def test_bucket_discriminator(self):
        """BucketConfig discriminates by type field."""
        strategy = OrderBasedStrategy(
            type="order_based",
            bucket_config={"type": "manual", "width_percent": 0.05},
        )
        assert isinstance(strategy.bucket_config, ManualBucketConfig)

        strategy = OrderBasedStrategy(
            type="order_based",
            bucket_config={"type": "auto"},
        )
        assert isinstance(strategy.bucket_config, AutoBucketConfig)


class TestTraderConfigUpdateSchema:
    """Tests for TraderConfigUpdateSchema - update-specific model."""

    def test_self_account_address_optional(self):
        """TraderConfigUpdateSchema allows self_account.address to be optional."""
        config_data = {
            "provider_settings": {
                "network": "mainnet",
                "self_account": {"is_sub": False},
                "copy_account": {"address": COPY_ADDR},
                "risk_parameters": {"allowed_assets": "*"},
            },
            "trader_settings": {
                "trading_strategy": {"type": "position_based"},
            },
        }

        config = TraderConfigUpdateSchema(**config_data)
        assert config.provider_settings.self_account.address is None
        assert config.provider_settings.self_account.is_sub is False

    def test_self_account_address_can_be_provided(self):
        """TraderConfigUpdateSchema allows self_account.address to be provided explicitly."""
        config_data = {
            "provider_settings": {
                "network": "mainnet",
                "self_account": {"address": SELF_ADDR, "is_sub": True},
                "copy_account": {"address": COPY_ADDR},
                "risk_parameters": {"allowed_assets": "*"},
            },
            "trader_settings": {
                "trading_strategy": {"type": "position_based"},
            },
        }

        config = TraderConfigUpdateSchema(**config_data)
        assert config.provider_settings.self_account.address == SELF_ADDR
        assert config.provider_settings.self_account.is_sub is True

    def test_self_account_defaults_to_empty_object(self):
        """TraderConfigUpdateSchema uses default factory for self_account."""
        config_data = {
            "provider_settings": {
                "network": "mainnet",
                "copy_account": {"address": COPY_ADDR},
                "risk_parameters": {"allowed_assets": "*"},
            },
            "trader_settings": {
                "trading_strategy": {"type": "position_based"},
            },
        }

        config = TraderConfigUpdateSchema(**config_data)
        assert config.provider_settings.self_account.address is None
        assert config.provider_settings.self_account.is_sub is False
