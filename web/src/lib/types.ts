/**
 * TypeScript types matching the HyperTrader API.
 * 
 * These types should be kept in sync with the backend Pydantic schemas.
 */

export interface User {
  id: string;
  privy_user_id: string;
  wallet_address: string;
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
  k8s_name: string;
  status: TraderStatus;
  image_tag: string;
  created_at: string;
  updated_at: string;
  latest_config?: Record<string, any>;
}

export interface CreateTraderRequest {
  wallet_address: string;
  private_key: string; // Deprecated - not used with Privy
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

export interface K8sStatus {
  pod_phase: string;
  ready: boolean;
  restarts: number;
  pod_ip?: string;
  node?: string;
  started_at?: string;
}

export interface TraderStatusResponse {
  id: string;
  wallet_address: string;
  k8s_name: string;
  status: string;
  k8s_status: K8sStatus;
}

export interface LogLine {
  timestamp: string;
  message: string;
}

export interface TraderLogsResponse {
  trader_id: string;
  logs: string[];
  total_lines: number;
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
