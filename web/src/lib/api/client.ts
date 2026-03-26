import { config } from '../../config';
import type {
  User,
  Trader,
  CreateTraderRequest,
  TraderStatusResponse,
  TraderLogsResponse,
  SystemStats,
  LoginRequest,
  LoginResponse,
} from '../types';

const API_BASE = config.VITE_API_URL;

class ApiClient {
  private token: string | null = null;

  constructor() {
    // Attempt to load token from localStorage on init
    if (typeof window !== 'undefined') {
      const storedToken = localStorage.getItem('auth_token');
      if (storedToken) {
        this.token = storedToken;
      }
    }
  }

  setToken(token: string | null): void {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      // Token expired or invalid
      this.setToken(null);
      // Optional: redirect to login or emit event
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          // window.location.href = '/login'; // Let the app handle redirection via router
      }
      throw new Error('Authentication required');
    }
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      
      if (response.status === 422) {
        if (error.detail && Array.isArray(error.detail)) {
          const messages = error.detail.map((e: any) => {
            const field = e.loc ? e.loc[e.loc.length - 1] : 'field';
            const msg = e.msg || e.message || 'Invalid value';
            return `${field}: ${msg}`;
          });
          throw new Error(messages.join('\n'));
        }
      }
      
      throw new Error(error.detail || 'Request failed');
    }
    
    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }
  
  // Auth endpoints
  async login(data: LoginRequest): Promise<LoginResponse> {
    // Map username -> email for backend
    const backendData = {
      email: data.username,
      password: data.password,
    };

    const response = await this.request<any>('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(backendData),
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    this.setToken(response.access_token);
    
    // Map backend user (email) to frontend user (username)
    const frontendUser: User = {
      ...response.user,
      username: response.user.email,
    };
    
    return {
      ...response,
      user: frontendUser,
    };
  }

  async logout(): Promise<void> {
    try {
      // Best effort logout on server
      // We need refresh token for logout endpoint usually, or just revoke current session
      // The backend logout endpoint takes refresh_token in body
      // We don't have refresh token stored in this simple client implementation (only access token)
      // So we can't call logout properly without storing refresh token separately.
      // For now, just clear local token.
      // await this.request('/v1/auth/logout', { method: 'POST' });
    } catch (e) {
      // Ignore error
    }
    this.setToken(null);
  }

  async me(): Promise<User> {
    const user = await this.request<any>('/v1/auth/me');
    return {
      ...user,
      username: user.email,
    };
  }
  
  // Trader endpoints
  async listTraders(): Promise<Trader[]> {
    const response = await this.request<{ traders: any[], count: number }>('/v1/traders');
    // Map backend trader (k8s_name) to frontend trader (runtime_name)
    return response.traders.map(t => ({
      ...t,
      runtime_name: t.k8s_name, // Map k8s_name -> runtime_name
      // Map k8s_status -> runtime_status (if present)
      // Wait, list response uses TraderResponse which has status but not k8s_status
    }));
  }
  
  async getTrader(id: string): Promise<Trader> {
    const t = await this.request<any>(`/v1/traders/${id}`);
    return {
      ...t,
      runtime_name: t.k8s_name,
    };
  }
  
  async createTrader(data: CreateTraderRequest): Promise<Trader> {
    const t = await this.request<any>('/v1/traders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return {
      ...t,
      runtime_name: t.k8s_name,
    };
  }
  
  async deleteTrader(id: string): Promise<void> {
    await this.request(`/v1/traders/${id}`, {
      method: 'DELETE',
    });
  }
  
  async startTrader(id: string): Promise<void> {
    await this.request(`/v1/traders/${id}/restart`, { // Backend uses restart for now
      method: 'POST',
    });
  }
  
  async stopTrader(_id: string): Promise<void> {
     // Backend doesn't support stop yet, maybe simulate or ignore
     // Or maybe DELETE deployment but keep DB record?
     // For now, just log warning or fail gracefully if needed.
     // I'll comment out the request to avoid 404
     console.warn('stopTrader not implemented on backend');
  }
  
  async restartTrader(id: string): Promise<void> {
    await this.request(`/v1/traders/${id}/restart`, {
      method: 'POST',
    });
  }
  
  async getTraderStatus(id: string): Promise<TraderStatusResponse> {
    const status = await this.request<any>(`/v1/traders/${id}/status`);
    return {
      ...status,
      runtime_name: status.k8s_name,
      runtime_status: status.k8s_status, // Map k8s_status -> runtime_status
    };
  }
  
  async getTraderLogs(id: string, lines?: number): Promise<string[]> {
    const params = lines ? `?tail_lines=${lines}` : ''; // Backend uses tail_lines
    const response = await this.request<TraderLogsResponse>(`/v1/traders/${id}/logs${params}`);
    return response.logs.split('\n');
  }
  
  // Admin endpoints
  async adminListUsers(skip = 0, limit = 100): Promise<User[]> {
    const users = await this.request<any[]>(`/v1/admin/users?skip=${skip}&limit=${limit}`);
    return users.map(u => ({
      ...u,
      username: u.email,
    }));
  }
  
  async adminListTraders(skip = 0, limit = 100): Promise<Trader[]> {
    const traders = await this.request<any[]>(`/v1/admin/traders?skip=${skip}&limit=${limit}`);
    return traders.map(t => ({
      ...t,
      runtime_name: t.k8s_name,
    }));
  }
  
  async adminGetStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/v1/admin/stats');
  }
}

export const api = new ApiClient();
