import { setTokenGetter, getToken } from "./api/client";
import type {
  User,
  Trader,
  TraderListResponse,
  TraderStatusResponse,
  CreateTraderRequest,
  UpdateTraderRequest,
  UpdateTraderInfoRequest,
  SystemStats,
  LoginResponse,
  SetupStatusResponse,
  SSLStatusResponse,
  StartResponse,
  StopResponse,
  ImageVersionInfo,
} from "./types";
import { config } from "~/config";

const baseUrl = config.VITE_API_URL;

async function fetchJson<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = await getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options?.headers,
  };

  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 && window.location.pathname !== "/") {
      window.location.href = "/";
    }
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  setAuthTokenGetter: setTokenGetter,

  // Auth
  async login(username: string, password: string): Promise<LoginResponse> {
    return fetchJson("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  async logout(): Promise<void> {
    await fetchJson("/v1/auth/logout", { method: "POST" });
  },

  async me(): Promise<User> {
    return fetchJson("/v1/auth/me");
  },

  async getSetupStatus(): Promise<SetupStatusResponse> {
    return fetchJson("/v1/auth/setup-status");
  },

  async bootstrap(username: string, password: string): Promise<LoginResponse> {
    return fetchJson("/v1/auth/bootstrap", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  // Traders
  async listTraders(): Promise<Trader[]> {
    const response = await fetchJson<TraderListResponse>("/v1/traders/");
    return response.traders;
  },

  async getTrader(id: string): Promise<Trader> {
    return fetchJson(`/v1/traders/${id}`);
  },

  async createTrader(data: CreateTraderRequest): Promise<Trader> {
    return fetchJson("/v1/traders/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateTrader(id: string, data: UpdateTraderRequest): Promise<Trader> {
    return fetchJson(`/v1/traders/${id}/config`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async updateTraderInfo(
    traderId: string,
    data: UpdateTraderInfoRequest
  ): Promise<Trader> {
    // Only send fields that have values
    const payload: UpdateTraderInfoRequest = {};
    if (data.name !== undefined && data.name !== "") {
      payload.name = data.name;
    }
    if (data.description !== undefined && data.description !== "") {
      payload.description = data.description;
    }
    const response = await fetchJson<Trader>(`/v1/traders/${traderId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return response;
  },

  async deleteTrader(id: string): Promise<void> {
    return fetchJson(`/v1/traders/${id}`, { method: "DELETE" });
  },

  async restartTrader(id: string): Promise<void> {
    return fetchJson(`/v1/traders/${id}/restart`, { method: "POST" });
  },

  async startTrader(id: string): Promise<StartResponse> {
    return fetchJson(`/v1/traders/${id}/start`, { method: "POST" });
  },

  async stopTrader(id: string): Promise<StopResponse> {
    return fetchJson(`/v1/traders/${id}/stop`, { method: "POST" });
  },

  async getImageVersions(): Promise<ImageVersionInfo> {
    return fetchJson("/v1/images");
  },

  async updateTraderImage(id: string, newTag: string): Promise<Trader> {
    return fetchJson(`/v1/traders/${id}/update-image`, {
      method: "POST",
      body: JSON.stringify({ new_tag: newTag }),
    });
  },

  async getTraderStatus(id: string): Promise<TraderStatusResponse> {
    return fetchJson(`/v1/traders/${id}/status`);
  },

  async getTraderLogs(id: string, lines = 100): Promise<string[]> {
    return fetchJson(`/v1/traders/${id}/logs?lines=${lines}`);
  },

  // SSL Setup
  async getSSLStatus(): Promise<SSLStatusResponse> {
    return fetchJson("/v1/setup/ssl-status");
  },

  async configureSSL(domain: string, email: string): Promise<{ success: boolean; message: string; redirect_url: string }> {
    return fetchJson("/v1/setup/ssl", {
      method: "POST",
      body: JSON.stringify({ mode: "domain", domain, email }),
    });
  },

  // Admin
  async adminListUsers(skip = 0, limit = 100): Promise<User[]> {
    return fetchJson(`/v1/admin/users?skip=${skip}&limit=${limit}`);
  },

  async adminListTraders(skip = 0, limit = 100): Promise<Trader[]> {
    return fetchJson(`/v1/admin/traders?skip=${skip}&limit=${limit}`);
  },

  async adminGetStats(): Promise<SystemStats> {
    return fetchJson("/v1/admin/stats");
  },
};
