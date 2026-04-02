export interface User {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export interface Trader {
  id: string;
  name: string;
  wallet_address: string;
  status: "running" | "stopped" | "error";
  created_at: string;
  updated_at: string;
  user_id: string;
}

export interface TraderStatusResponse {
  status: "running" | "stopped" | "error";
  uptime_seconds?: number;
  last_error?: string;
}

export interface CreateTraderRequest {
  name: string;
  wallet_address: string;
  private_key: string;
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
