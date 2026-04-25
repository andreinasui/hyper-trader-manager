"""
Trader configuration schema for HyperTrader API.

Pydantic v2 models matching the HyperTrader YAML config schema.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SelfAccount(BaseModel):
    """Self trading account configuration."""

    address: str = Field(
        ...,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Ethereum address (0x...)",
    )
    is_sub: bool = Field(
        default=False,
        description="Whether account is a vault sub-account",
    )


class CopyAccount(BaseModel):
    """Account to copy trades from."""

    address: str = Field(
        ...,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Ethereum address (0x...)",
    )


class ProviderSettings(BaseModel):
    """Exchange and account configuration."""

    exchange: Literal["hyperliquid"] = Field(
        default="hyperliquid",
        description="Exchange identifier",
    )
    network: Literal["mainnet", "testnet"] = Field(
        ...,
        description="Network environment",
    )
    self_account: SelfAccount = Field(
        ...,
        description="Your trading account",
    )
    copy_account: CopyAccount = Field(
        ...,
        description="Account to copy trades from",
    )
    slippage_bps: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="Slippage tolerance in basis points (1bp = 0.01%)",
    )
    builder_fee_bps: int = Field(
        default=0,
        ge=0,
        le=200,
        description="Builder fee in basis points",
    )


class OpenOnLowPnl(BaseModel):
    """Configuration for opening positions on low PnL."""

    enabled: bool = Field(default=True)
    max_pnl: float = Field(
        default=0.05,
        ge=-1.0,
        le=1.0,
        description="Max PnL threshold (-1.0 to 1.0)",
    )


class RiskParameters(BaseModel):
    """Risk management parameters."""

    allowed_assets: list[str] | None = Field(
        default=None,
        description="Whitelist of assets (null = all allowed)",
    )
    blocked_assets: list[str] = Field(
        default_factory=list,
        description="Blacklist of assets",
    )
    max_leverage: int | None = Field(
        default=None,
        ge=1,
        le=40,
        description="Maximum leverage allowed for positions",
    )
    self_proportionality_multiplier: float = Field(
        default=1.0,
        ge=0.01,
        le=10.0,
        description="Multiplier for self order sizing",
    )
    open_on_low_pnl: OpenOnLowPnl = Field(
        default_factory=OpenOnLowPnl,
    )


class ManualBucket(BaseModel):
    """Fixed bucket width configuration."""

    width_percent: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="Bucket width as percentage (0-1)",
    )


class AutoBucket(BaseModel):
    """Auto-detection bucket configuration."""

    ratio_threshold: float = Field(
        default=1000.0,
        gt=0.0,
        description="Ratio threshold for auto-detection",
    )
    wide_bucket_percent: float = Field(
        default=0.01,
        gt=0.0,
        le=1.0,
        description="Wide bucket percentage",
    )
    narrow_bucket_percent: float = Field(
        default=0.0001,
        gt=0.0,
        le=1.0,
        description="Narrow bucket percentage",
    )


class BucketConfig(BaseModel):
    """Order bucketing configuration."""

    manual: ManualBucket | None = Field(
        default=None,
        description="Fixed bucket width",
    )
    auto: AutoBucket | None = Field(
        default=None,
        description="Auto-detection mode",
    )
    pricing_strategy: Literal["vwap", "aggressive"] = Field(
        default="vwap",
        description="Bucket price calculation strategy",
    )

    model_config = ConfigDict(
        json_schema_extra={"description": "Either manual or auto must be set, not both"}
    )


class TradingStrategy(BaseModel):
    """Trading strategy configuration."""

    type: Literal["order_based"] = Field(
        default="order_based",
        description="Trading strategy type",
    )
    risk_parameters: RiskParameters = Field(
        default_factory=RiskParameters,
    )
    bucket_config: BucketConfig = Field(
        default_factory=BucketConfig,
        description="Order bucketing configuration",
    )


class TraderSettings(BaseModel):
    """Trading strategy and risk parameters."""

    min_self_funds: int = Field(
        default=1,
        ge=1,
        description="Minimum USDC in self account to start trading",
    )
    min_copy_funds: int = Field(
        default=1,
        ge=1,
        description="Minimum USDC in copy account to start trading",
    )
    trading_strategy: TradingStrategy = Field(
        ...,
        description="Trading strategy configuration",
    )


class TraderConfigSchema(BaseModel):
    """Complete trader configuration schema."""

    provider_settings: ProviderSettings = Field(
        ...,
        description="Exchange and account configuration",
    )
    trader_settings: TraderSettings = Field(
        ...,
        description="Trading strategy and risk parameters",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider_settings": {
                    "exchange": "hyperliquid",
                    "network": "mainnet",
                    "self_account": {
                        "address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                        "is_sub": False,
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
                        "risk_parameters": {
                            "max_leverage": 10,
                        },
                    },
                },
            }
        }
    )


# Update-specific schemas where self_account.address is optional
# (will be auto-filled from trader's wallet_address in the service layer)


class SelfAccountUpdate(BaseModel):
    """Self account for updates - address is optional (auto-filled from trader)."""

    address: str | None = Field(
        default=None,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Ethereum address (0x...) - auto-filled if not provided",
    )
    is_sub: bool = Field(
        default=False,
        description="Whether account is a vault sub-account",
    )


class ProviderSettingsUpdate(BaseModel):
    """Exchange and account configuration for updates."""

    exchange: Literal["hyperliquid"] = Field(
        default="hyperliquid",
        description="Exchange identifier",
    )
    network: Literal["mainnet", "testnet"] = Field(
        ...,
        description="Network environment",
    )
    self_account: SelfAccountUpdate = Field(
        default_factory=SelfAccountUpdate,
        description="Your trading account (address auto-filled)",
    )
    copy_account: CopyAccount = Field(
        ...,
        description="Account to copy trades from",
    )
    slippage_bps: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="Slippage tolerance in basis points (1bp = 0.01%)",
    )
    builder_fee_bps: int = Field(
        default=0,
        ge=0,
        le=200,
        description="Builder fee in basis points",
    )


class TraderConfigUpdateSchema(BaseModel):
    """Trader configuration for updates - self_account.address is optional."""

    provider_settings: ProviderSettingsUpdate = Field(
        ...,
        description="Exchange and account configuration",
    )
    trader_settings: TraderSettings = Field(
        ...,
        description="Trading strategy and risk parameters",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider_settings": {
                    "exchange": "hyperliquid",
                    "network": "mainnet",
                    "self_account": {
                        "is_sub": False,
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
                        "risk_parameters": {
                            "max_leverage": 10,
                        },
                    },
                },
            }
        }
    )
