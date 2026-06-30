import type { TraderConfig as SchemaTraderConfig } from "~/lib/schemas/trader-config";

export interface User {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export type TraderConfig = SchemaTraderConfig;

export interface Trader {
  id: string;
  user_id: string;
  wallet_address: string;
  runtime_name: string;
  status: "configured" | "starting" | "running" | "stopping" | "stopped" | "failed";
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
  ssl_configured: boolean;
  mode?: "domain";
  domain?: string;
  configured_at?: string;
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

export interface TraderLogArchive {
  id: string;
  trader_id: string;
  run_started_at: string;
  run_ended_at: string;
  file_size_bytes: number;
  created_at: string;
}
