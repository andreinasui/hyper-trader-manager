/**
 * TypeScript types matching the HyperTrader API.
 * 
 * These types should be kept in sync with the backend Pydantic schemas.
 */

export interface User {
  id: string;
  username: string;
  email: string;
  plan_tier?: string;
  is_admin: boolean;
  created_at: string;
}

export type TraderStatus = "pending" | "approving_agent" | "deploying" | "running" | "stopped" | "error";
export type ExchangeType = "hyperliquid";
export type NetworkType = "mainnet" | "testnet";

export interface Trader {
  id: string;
  user_id: string;
  name?: string;
  wallet_address: string;
  agent_address: string;
  runtime_name: string;
  status: TraderStatus;
  image_tag: string;
  created_at: string;
  updated_at: string;
  latest_config?: Record<string, any>;
}

export interface CreateTraderRequest {
  wallet_address: string;
  private_key: string;
  config: {
    name: string;
    exchange: ExchangeType;
    self_account: {
      address: string;
      base_url: NetworkType;
    };
    copy_account: {
      address: string;
      base_url: NetworkType;
    };
  };
}

export interface TraderDetails extends Trader {
  config?: Record<string, any>;
}

export interface RuntimeStatus {
  status: string;
  container_id?: string;
  image_id?: string;
  restarts: number;
  started_at?: string;
}

export interface TraderStatusResponse {
  id: string;
  wallet_address: string;
  runtime_name: string;
  status: string;
  runtime_status: RuntimeStatus;
}

export interface LogLine {
  timestamp: string;
  message: string;
}

export interface TraderLogsResponse {
  trader_id: string;
  logs: string; // Backend returns single string
  tail_lines: number; // Backend uses tail_lines
}

export interface SystemStats {
  total_users: number;
  total_traders: number;
  traders_by_status: Record<string, number>;
  users_by_plan: Record<string, number>;
}

export interface ValidationError {
  type: string;
  loc: string[];
  msg: string;
  input?: any;
}

export interface ApiError {
  detail: string | ValidationError[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}
