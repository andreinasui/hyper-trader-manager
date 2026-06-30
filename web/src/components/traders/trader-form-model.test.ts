import { describe, expect, it } from "vitest";
import type { Trader } from "~/lib/types";
import type { TraderConfig } from "~/lib/schemas/trader-config";
import {
  buildInitialTraderForm,
  defaultTraderFormValues,
  normalizeTraderConfig,
  prepareTraderFormValues,
  toCreateTraderRequest,
  toUpdateTraderRequests,
  type TraderFormValues,
  validateTraderForm,
} from "./trader-form-model";

const wallet = "0x1111111111111111111111111111111111111111";
const copy = "0x2222222222222222222222222222222222222222";
const privateKey = "0x1111111111111111111111111111111111111111111111111111111111111111";

const config: TraderConfig = {
  provider_settings: {
    exchange: "hyperliquid",
    network: "testnet",
    self_account: { address: wallet, is_sub: true },
    copy_account: { address: copy },
    slippage_bps: 42,
    risk_parameters: {
      allowed_assets: ["BTC"],
      blocked_assets: ["ETH"],
      max_leverage: 10,
    },
  },
  trader_settings: {
    trading_strategy: {
      type: "order_based",
      risk_parameters: {
        self_proportionality_multiplier: 2,
        open_on_low_pnl: { enabled: true, max_pnl: 0.07 },
      },
      bucket_config: {
        type: "manual",
        width_percent: 0.03,
        pricing_strategy: "aggressive",
      },
    },
  },
};

const trader: Trader = {
  id: "trader-1",
  user_id: "user-1",
  wallet_address: wallet,
  runtime_name: "runtime",
  status: "configured",
  image_tag: "1.0.0",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
  latest_config: config,
  start_attempts: 0,
  last_error: null,
  stopped_at: null,
  name: "Alpha",
  description: "Copies BTC",
  display_name: "Alpha",
};

describe("trader-form-model", () => {
  it("builds create defaults once", () => {
    expect(defaultTraderFormValues.config.provider_settings.network).toBe("mainnet");
    expect(defaultTraderFormValues.config.provider_settings.slippage_bps).toBe(200);
    expect(defaultTraderFormValues.config.trader_settings.trading_strategy.bucket_config.type).toBe("auto");
  });

  it("builds edit values from a trader", () => {
    const values = buildInitialTraderForm("edit", trader);

    expect(values.name).toBe("Alpha");
    expect(values.description).toBe("Copies BTC");
    expect(values.wallet_address).toBe(wallet);
    expect(values.private_key).toBe("");
    expect(values.config.provider_settings.network).toBe("testnet");
    expect(values.config.provider_settings.risk_parameters.allowed_assets).toEqual(["BTC"]);
    expect(values.config.provider_settings.risk_parameters.blocked_assets).toEqual(["ETH"]);
    expect(values.config.trader_settings.trading_strategy.bucket_config).toEqual({
      type: "manual",
      width_percent: 0.03,
      pricing_strategy: "aggressive",
    });
  });

  it("normalizes legacy config with missing bucket_config", () => {
    const legacy = structuredClone(config) as TraderConfig;
    delete (legacy.trader_settings.trading_strategy as Partial<typeof legacy.trader_settings.trading_strategy>).bucket_config;

    expect(normalizeTraderConfig(legacy).trader_settings.trading_strategy.bucket_config).toEqual({
      type: "auto",
      pricing_strategy: "vwap",
      ratio_threshold: 1000,
      wide_bucket_percent: 0.01,
      narrow_bucket_percent: 0.0001,
    });
  });

  it("keeps discriminated manual bucket config without auto defaults", () => {
    expect(normalizeTraderConfig(config).trader_settings.trading_strategy.bucket_config).toEqual({
      type: "manual",
      width_percent: 0.03,
      pricing_strategy: "aggressive",
    });
  });

  it("derives self account from wallet before create submit", () => {
    const request = toCreateTraderRequest({
      ...defaultTraderFormValues,
      wallet_address: wallet,
      private_key: privateKey,
      name: "  Alpha  ",
      description: "  Copies BTC  ",
      config: {
        ...defaultTraderFormValues.config,
        provider_settings: {
          ...defaultTraderFormValues.config.provider_settings,
          copy_account: { address: copy },
        },
      },
    });

    expect(request.name).toBe("Alpha");
    expect(request.description).toBe("Copies BTC");
    expect(request.config.provider_settings.self_account.address).toBe(wallet);
    expect(request.config.provider_settings.risk_parameters).toEqual({
      allowed_assets: "*",
      blocked_assets: [],
      max_leverage: 50,
    });
    expect(request.config.trader_settings.trading_strategy.bucket_config).toEqual({
      type: "auto",
      pricing_strategy: "vwap",
      ratio_threshold: 1000,
      wide_bucket_percent: 0.01,
      narrow_bucket_percent: 0.0001,
    });
  });

  it("strips stale manual bucket fields before submit", () => {
    const values = buildInitialTraderForm("edit", trader);
    values.config.trader_settings.trading_strategy.bucket_config = {
      type: "auto",
      ratio_threshold: 500,
      wide_bucket_percent: 0.008,
      narrow_bucket_percent: 0.0002,
      pricing_strategy: "aggressive",
      width_percent: 0.03,
    } as TraderFormValues["config"]["trader_settings"]["trading_strategy"]["bucket_config"];

    const bucket = prepareTraderFormValues(values).config.trader_settings.trading_strategy.bucket_config;

    expect(bucket).toEqual({
      type: "auto",
      ratio_threshold: 500,
      wide_bucket_percent: 0.008,
      narrow_bucket_percent: 0.0002,
      pricing_strategy: "aggressive",
    });
    expect("width_percent" in bucket).toBe(false);
  });

  it("prepares proxied form values from modular forms", () => {
    const values = buildInitialTraderForm("edit", trader);
    values.config.provider_settings.risk_parameters.blocked_assets = new Proxy(["ETH"], {});

    expect(() => prepareTraderFormValues(values)).not.toThrow();
    expect(prepareTraderFormValues(values).config.provider_settings.risk_parameters.blocked_assets).toEqual(["ETH"]);
  });

  it("strips stale auto bucket fields before submit", () => {
    const values = buildInitialTraderForm("create");
    values.config.trader_settings.trading_strategy.bucket_config = {
      type: "manual",
      width_percent: 0.03,
      pricing_strategy: "vwap",
      ratio_threshold: 500,
      wide_bucket_percent: 0.008,
      narrow_bucket_percent: 0.0002,
    } as TraderFormValues["config"]["trader_settings"]["trading_strategy"]["bucket_config"];

    const bucket = prepareTraderFormValues(values).config.trader_settings.trading_strategy.bucket_config;

    expect(bucket).toEqual({ type: "manual", width_percent: 0.03, pricing_strategy: "vwap" });
    expect("ratio_threshold" in bucket).toBe(false);
    expect("wide_bucket_percent" in bucket).toBe(false);
    expect("narrow_bucket_percent" in bucket).toBe(false);
  });

  it("returns separate existing update payloads", () => {
    const { info, config: updateConfig } = toUpdateTraderRequests(buildInitialTraderForm("edit", trader));

    expect(info).toEqual({ name: "Alpha", description: "Copies BTC" });
    expect(updateConfig.config.provider_settings.self_account.address).toBe(wallet);
    expect(updateConfig.config.provider_settings.risk_parameters).toEqual({
      allowed_assets: ["BTC"],
      blocked_assets: ["ETH"],
      max_leverage: 10,
    });
    expect(updateConfig.config.trader_settings.trading_strategy.bucket_config).toEqual({
      type: "manual",
      width_percent: 0.03,
      pricing_strategy: "aggressive",
    });
  });

  it("omits blank name and description rather than clearing them", () => {
    const { info } = toUpdateTraderRequests({
      ...buildInitialTraderForm("edit", trader),
      name: "  ",
      description: "  ",
    });

    expect(info).toEqual({});
  });

  it("validates partial values merged with initial values", () => {
    const initial = buildInitialTraderForm("edit", trader);
    const errors = validateTraderForm("edit", initial, {
      config: {
        provider_settings: {
          copy_account: { address: "not-an-address" },
        },
      },
    });

    expect(errors["config.provider_settings.copy_account.address"]).toBe("Invalid Ethereum address");
  });
});
