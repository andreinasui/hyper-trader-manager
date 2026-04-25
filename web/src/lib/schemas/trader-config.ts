import { z } from "zod";

const ethereumAddressRegex = /^0x[a-fA-F0-9]{40}$/;

export const selfAccountSchema = z.object({
  address: z.string().regex(ethereumAddressRegex, "Invalid Ethereum address"),
  is_sub: z.boolean().default(false),
});

// For form validation, self_account.address can be empty (auto-filled from wallet_address)
export const selfAccountFormSchema = z.object({
  address: z.string().default(""),
  is_sub: z.boolean().default(false),
});

export const copyAccountSchema = z.object({
  address: z.string().regex(ethereumAddressRegex, "Invalid Ethereum address"),
});

export const providerSettingsSchema = z.object({
  exchange: z.literal("hyperliquid").default("hyperliquid"),
  network: z.enum(["mainnet", "testnet"]),
  self_account: selfAccountSchema,
  copy_account: copyAccountSchema,
  slippage_bps: z.number().int().min(0).max(1000).default(200),
  builder_fee_bps: z.number().int().min(0).max(200).default(0),
});

// For form validation, uses relaxed self_account validation
export const providerSettingsFormSchema = z.object({
  exchange: z.literal("hyperliquid").default("hyperliquid"),
  network: z.enum(["mainnet", "testnet"]),
  self_account: selfAccountFormSchema,
  copy_account: copyAccountSchema,
  slippage_bps: z.number().int().min(0).max(1000).default(200),
  builder_fee_bps: z.number().int().min(0).max(200).default(0),
});

export const openOnLowPnlSchema = z.object({
  enabled: z.boolean().default(true),
  max_pnl: z.number().min(-1).max(1).default(0.05),
});

export const riskParametersSchema = z.object({
  allowed_assets: z.array(z.string()).nullable().optional(),
  blocked_assets: z.array(z.string()).default([]),
  max_leverage: z.number().int().min(1).max(50).nullable().optional(),
  self_proportionality_multiplier: z.number().min(0.01).max(10).default(1.0),
  open_on_low_pnl: openOnLowPnlSchema.default({}),
});

export const manualBucketSchema = z.object({
  width_percent: z.number().gt(0).lte(1),
});

export const autoBucketSchema = z.object({
  ratio_threshold: z.number().gt(0).default(1000),
  wide_bucket_percent: z.number().gt(0).lte(1).default(0.01),
  narrow_bucket_percent: z.number().gt(0).lte(1).default(0.0001),
});

export const bucketConfigSchema = z
  .object({
    manual: manualBucketSchema.nullable().optional(),
    auto: autoBucketSchema.nullable().optional(),
    pricing_strategy: z.enum(["vwap", "aggressive"]).default("vwap"),
  })
  .refine((data) => !(data.manual && data.auto), {
    message: "Cannot use both manual and auto bucket config",
  });

export const tradingStrategySchema = z.object({
  type: z.enum(["order_based", "position_based"]).default("order_based"),
  risk_parameters: riskParametersSchema.default({}),
  bucket_config: bucketConfigSchema.default({ pricing_strategy: "vwap" }),
});

export const traderSettingsSchema = z.object({
  min_self_funds: z.number().int().min(1).default(1),
  min_copy_funds: z.number().int().min(1).default(1),
  trading_strategy: tradingStrategySchema.default({}),
});

export const traderConfigSchema = z.object({
  provider_settings: providerSettingsSchema,
  trader_settings: traderSettingsSchema,
});

// Form-specific config schema with relaxed self_account validation
export const traderConfigFormSchema = z.object({
  provider_settings: providerSettingsFormSchema,
  trader_settings: traderSettingsSchema,
});

export type TraderConfig = z.infer<typeof traderConfigSchema>;
export type ProviderSettings = z.infer<typeof providerSettingsSchema>;
export type TraderSettings = z.infer<typeof traderSettingsSchema>;
export type TradingStrategy = z.infer<typeof tradingStrategySchema>;
export type RiskParameters = z.infer<typeof riskParametersSchema>;
export type BucketConfig = z.infer<typeof bucketConfigSchema>;

// Form-specific schema that includes wallet credentials
// Uses relaxed validation for self_account.address (auto-filled from wallet_address)
export const createTraderFormSchema = z
  .object({
    wallet_address: z
      .string()
      .regex(ethereumAddressRegex, "Invalid Ethereum address"),
    private_key: z
      .string()
      .regex(/^0x[a-fA-F0-9]{64}$/, "Invalid private key format"),
    name: z.string().max(50).optional(),
    description: z.string().max(255).optional(),
    config: traderConfigFormSchema,
  })
  .refine(
    (data) =>
      data.config.provider_settings.copy_account.address.toLowerCase() !==
      data.wallet_address.toLowerCase(),
    {
      message: "Copy account cannot be the same as your wallet",
      path: ["config", "provider_settings", "copy_account", "address"],
    }
  );

export type CreateTraderForm = z.infer<typeof createTraderFormSchema>;

// Edit form schema - only validates config, wallet_address and private_key are optional
export const editTraderFormSchema = z.object({
  wallet_address: z.string().optional(),
  private_key: z.string().optional(),
  config: traderConfigFormSchema,
});

export type EditTraderForm = z.infer<typeof editTraderFormSchema>;
