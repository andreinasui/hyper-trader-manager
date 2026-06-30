import type { PartialValues } from "@modular-forms/solid";
import {
  createTraderFormSchema,
  editTraderFormSchema,
  type BucketConfig,
  type CreateTraderForm,
  type TraderConfig,
} from "~/lib/schemas/trader-config";
import type { CreateTraderRequest, Trader, UpdateTraderInfoRequest, UpdateTraderRequest } from "~/lib/types";

export type TraderFormMode = "create" | "edit";
export type TraderFormValues = CreateTraderForm;

export const TRADER_FORM_DEFAULTS = {
  multiplier: 1.0,
  maxPnl: 0.05,
  maxLeverage: 50,
  maxLeverageMin: 1,
  maxLeverageMax: 50,
  slippageBps: 200,
  ratioThreshold: 1000,
  wideBucketPct: 0.01,
  narrowBucketPct: 0.0001,
  widthPercent: 0.01,
} as const;

export const defaultTraderFormValues: TraderFormValues = {
  wallet_address: "",
  private_key: "",
  name: "",
  description: "",
  config: {
    provider_settings: {
      exchange: "hyperliquid",
      network: "mainnet",
      self_account: { address: "", is_sub: false },
      copy_account: { address: "" },
      slippage_bps: TRADER_FORM_DEFAULTS.slippageBps,
      risk_parameters: {
        allowed_assets: "*",
        blocked_assets: [],
        max_leverage: TRADER_FORM_DEFAULTS.maxLeverage,
      },
    },
    trader_settings: {
      trading_strategy: {
        type: "order_based",
        risk_parameters: {
          self_proportionality_multiplier: TRADER_FORM_DEFAULTS.multiplier,
          open_on_low_pnl: { enabled: true, max_pnl: TRADER_FORM_DEFAULTS.maxPnl },
        },
        bucket_config: {
          type: "auto",
          pricing_strategy: "vwap",
          ratio_threshold: TRADER_FORM_DEFAULTS.ratioThreshold,
          wide_bucket_percent: TRADER_FORM_DEFAULTS.wideBucketPct,
          narrow_bucket_percent: TRADER_FORM_DEFAULTS.narrowBucketPct,
        },
      },
    },
  },
};

export function deepMergeFormValues<T>(base: Partial<T>, next: Partial<T>): T {
  if (
    base &&
    next &&
    typeof base === "object" &&
    typeof next === "object" &&
    !Array.isArray(base) &&
    !Array.isArray(next)
  ) {
    const out: Record<string, unknown> = { ...(base as Record<string, unknown>) };
    for (const [key, value] of Object.entries(next as Record<string, unknown>)) {
      out[key] = key in out ? deepMergeFormValues(out[key] as never, value as never) : value;
    }
    return out as T;
  }
  return (next === undefined ? base : next) as T;
}

export function normalizeTraderConfig(config: TraderConfig): TraderConfig {
  const merged = deepMergeFormValues(defaultTraderFormValues.config, config);
  return {
    ...merged,
    trader_settings: {
      trading_strategy: {
        ...merged.trader_settings.trading_strategy,
        bucket_config: config.trader_settings.trading_strategy.bucket_config ??
          defaultTraderFormValues.config.trader_settings.trading_strategy.bucket_config,
      },
    },
  };
}

function stripStaleBucketFields(bucket: BucketConfig): BucketConfig {
  return bucket.type === "manual"
    ? { type: "manual", width_percent: bucket.width_percent, pricing_strategy: bucket.pricing_strategy }
    : {
      type: "auto",
      ratio_threshold: bucket.ratio_threshold,
      wide_bucket_percent: bucket.wide_bucket_percent,
      narrow_bucket_percent: bucket.narrow_bucket_percent,
      pricing_strategy: bucket.pricing_strategy,
    };
}

export function buildInitialTraderForm(mode: TraderFormMode, trader?: Trader): TraderFormValues {
  if (mode === "create") return structuredClone(defaultTraderFormValues);

  const values: TraderFormValues = deepMergeFormValues(defaultTraderFormValues, {
    wallet_address: trader?.wallet_address ?? "",
    private_key: "",
    name: trader?.name ?? "",
    description: trader?.description ?? "",
  } as Partial<TraderFormValues>);
  values.config = trader?.latest_config ? normalizeTraderConfig(trader.latest_config) : defaultTraderFormValues.config;
  return values;
}

export function prepareTraderFormValues(values: TraderFormValues): TraderFormValues {
  const prepared = toPlainObject(values) as TraderFormValues;
  prepared.config.provider_settings.self_account.address = prepared.wallet_address ?? "";
  prepared.config.trader_settings.trading_strategy.bucket_config = stripStaleBucketFields(
    prepared.config.trader_settings.trading_strategy.bucket_config
  );
  return prepared;
}

function toPlainObject(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toPlainObject);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, toPlainObject(child)]));
  }
  return value;
}

export function validateTraderForm(
  mode: TraderFormMode,
  initialValues: TraderFormValues,
  values: PartialValues<TraderFormValues>
): Record<string, string> {
  const merged = deepMergeFormValues(initialValues, values as Partial<TraderFormValues>);
  const result = (mode === "edit" ? editTraderFormSchema : createTraderFormSchema).safeParse(merged);
  if (result.success) return {};

  const errors: Record<string, string> = {};
  for (const error of result.error.errors) {
    errors[error.path.join(".")] = error.message;
  }
  return errors;
}

function trimmed(value: string | undefined): string | undefined {
  const next = value?.trim();
  return next ? next : undefined;
}

export function toCreateTraderRequest(values: TraderFormValues): CreateTraderRequest {
  const prepared = prepareTraderFormValues(values);
  return {
    wallet_address: prepared.wallet_address,
    private_key: prepared.private_key,
    config: prepared.config,
    ...(trimmed(prepared.name) ? { name: trimmed(prepared.name) } : {}),
    ...(trimmed(prepared.description) ? { description: trimmed(prepared.description) } : {}),
  };
}

export function toUpdateTraderRequests(values: TraderFormValues): {
  info: UpdateTraderInfoRequest;
  config: UpdateTraderRequest;
} {
  const prepared = prepareTraderFormValues(values);
  return {
    info: {
      ...(trimmed(prepared.name) ? { name: trimmed(prepared.name) } : {}),
      ...(trimmed(prepared.description) ? { description: trimmed(prepared.description) } : {}),
    },
    config: { config: prepared.config },
  };
}
