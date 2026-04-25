export interface User {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export interface TraderConfig {
  provider_settings: {
    exchange: "hyperliquid";
    network: "mainnet" | "testnet";
    self_account: {
      address: string;
      is_sub: boolean;
    };
    copy_account: {
      address: string;
    };
    slippage_bps: number;
    builder_fee_bps: number;
  };
  trader_settings: {
    min_self_funds: number;
    min_copy_funds: number;
    trading_strategy: {
      type: "order_based" | "position_based";
      risk_parameters: {
        allowed_assets?: string[] | null;
        blocked_assets: string[];
        max_leverage?: number | null;
        self_proportionality_multiplier: number;
        open_on_low_pnl: {
          enabled: boolean;
          max_pnl: number;
        };
      };
      bucket_config: {
        manual?: { width_percent: number } | null;
        auto?: {
          ratio_threshold: number;
          wide_bucket_percent: number;
          narrow_bucket_percent: number;
        } | null;
        pricing_strategy: "vwap" | "aggressive";
      };
    };
  };
}

export interface Trader {
  id: string;
  user_id: string;
  wallet_address: string;
  runtime_name: string;
  status: "configured" | "starting" | "running" | "stopped" | "failed";
  image_tag: string;
  created_at: string;
  updated_at: string;
  latest_config: TraderConfig | null;
  start_attempts: number;
  last_error: string | null;
  stopped_at: string | null;
  name: string | null;
  description: string | null;
  display_name: string;
}

export interface RuntimeStatus {
  state: "running" | "stopped" | "failed" | "pending" | "error" | "not_found" | "unknown" | "restarting";
  running: boolean;
  started_at?: string;
  exit_code?: number;
  replicas?: string;
  error?: string;
  restart_count?: number;
}

export interface TraderStatusResponse {
  id: string;
  wallet_address: string;
  runtime_name: string;
  status: Trader["status"];
  runtime_status: RuntimeStatus;
}

export interface CreateTraderRequest {
  wallet_address: string;
  private_key: string;
  config: TraderConfig;
  name?: string;
  description?: string;
  image_tag?: string;
}

export interface UpdateTraderRequest {
  config: TraderConfig;
}

export interface UpdateTraderInfoRequest {
  name?: string;
  description?: string;
}

export interface SystemStats {
  total_users: number;
  total_traders: number;
  active_traders: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface SetupStatusResponse {
  initialized: boolean;
}

export interface SSLStatusResponse {
  configured: boolean;
  mode?: "domain" | "ip";
  domain?: string;
}

export interface StartResponse {
  message: string;
  trader_id: string;
  runtime_name: string;
  status: string;
  start_attempts: number;
}

export interface StopResponse {
  message: string;
  trader_id: string;
  runtime_name: string;
  status: string;
}

export interface TraderListResponse {
  traders: Trader[];
  count: number;
}

export interface ImageVersionInfo {
  latest_local: string | null;
  all_local: string[];
  latest_remote: string | null;
  all_remote: string[];
}
