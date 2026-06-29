"""
Trader configuration schema for HyperTrader API.

Pydantic v2 models matching the HyperTrader JSON config schema.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SelfAccount(BaseModel):
    """Self trading account configuration."""

    model_config = ConfigDict(extra="forbid")

    address: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    is_sub: bool = False


class CopyAccount(BaseModel):
    """Account to copy trades from."""

    model_config = ConfigDict(extra="forbid")

    address: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")


class ProviderRiskParameters(BaseModel):
    """Provider-level risk management parameters."""

    model_config = ConfigDict(extra="forbid")

    allowed_assets: Literal["*"] | list[str] = Field(
        ...,
        description="'*' for all assets, or a non-empty list of asset names",
    )
    blocked_assets: list[str] = Field(default_factory=list)
    max_leverage: int | None = Field(default=None, ge=1, le=50)

    @field_validator("allowed_assets")
    @classmethod
    def _non_empty_list(cls, v: "Literal['*'] | list[str]") -> "Literal['*'] | list[str]":
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("allowed_assets must be '*' or a non-empty list")
        return v


class ProviderSettings(BaseModel):
    """Exchange and account configuration."""

    model_config = ConfigDict(extra="forbid")

    exchange: Literal["hyperliquid"] = "hyperliquid"
    network: Literal["mainnet", "testnet"]
    self_account: SelfAccount
    copy_account: CopyAccount
    slippage_bps: int = Field(default=200, ge=0, le=1000)
    risk_parameters: ProviderRiskParameters


class OpenOnLowPnl(BaseModel):
    """Configuration for opening positions when portfolio PnL is low."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    max_pnl: float = Field(default=0.0, ge=0.0, le=1.0)


class OrderBasedRiskParameters(BaseModel):
    """Risk parameters for order-based trading strategy."""

    model_config = ConfigDict(extra="forbid")

    self_proportionality_multiplier: float = Field(default=1.0, gt=0.0)
    open_on_low_pnl: OpenOnLowPnl = Field(default_factory=OpenOnLowPnl)


class AutoBucketConfig(BaseModel):
    """Auto-detection bucket configuration."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["auto"]
    ratio_threshold: float = Field(default=1000.0, ge=0.0)
    wide_bucket_percent: float = Field(default=0.01, gt=0.0, le=0.01)
    narrow_bucket_percent: float = Field(default=0.0001, ge=0.0, le=0.01)
    pricing_strategy: Literal["vwap", "aggressive"] = "vwap"


class ManualBucketConfig(BaseModel):
    """Fixed-width bucket configuration."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["manual"]
    width_percent: float = Field(..., ge=0.0, le=1.0)
    pricing_strategy: Literal["vwap", "aggressive"] = "vwap"


BucketConfig = Annotated[
    AutoBucketConfig | ManualBucketConfig,
    Field(discriminator="type"),
]


class PositionBasedStrategy(BaseModel):
    """Position-based trading strategy (no bucket config required)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["position_based"]


class OrderBasedStrategy(BaseModel):
    """Order-based trading strategy with required bucket config."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["order_based"]
    risk_parameters: OrderBasedRiskParameters = Field(default_factory=OrderBasedRiskParameters)
    bucket_config: BucketConfig


TradingStrategy = Annotated[
    PositionBasedStrategy | OrderBasedStrategy,
    Field(discriminator="type"),
]


class TraderSettings(BaseModel):
    """Trading strategy container."""

    model_config = ConfigDict(extra="forbid")

    trading_strategy: TradingStrategy


class TraderConfigSchema(BaseModel):
    """Complete trader configuration schema."""

    model_config = ConfigDict(extra="forbid")

    provider_settings: ProviderSettings
    trader_settings: TraderSettings


# Update-specific schemas where self_account.address is optional
# (auto-filled from trader's wallet_address in the service layer)


class SelfAccountUpdate(BaseModel):
    """Self account for updates - address is optional."""

    model_config = ConfigDict(extra="forbid")

    address: str | None = Field(default=None, pattern=r"^0x[a-fA-F0-9]{40}$")
    is_sub: bool = False


class ProviderSettingsUpdate(BaseModel):
    """Exchange and account configuration for updates."""

    model_config = ConfigDict(extra="forbid")

    exchange: Literal["hyperliquid"] = "hyperliquid"
    network: Literal["mainnet", "testnet"]
    self_account: SelfAccountUpdate = Field(default_factory=SelfAccountUpdate)
    copy_account: CopyAccount
    slippage_bps: int = Field(default=200, ge=0, le=1000)
    risk_parameters: ProviderRiskParameters


class TraderConfigUpdateSchema(BaseModel):
    """Trader configuration for updates - self_account.address is optional."""

    model_config = ConfigDict(extra="forbid")

    provider_settings: ProviderSettingsUpdate
    trader_settings: TraderSettings
