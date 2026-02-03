/**
 * Typed API client for HyperTrader API.
 * 
 * Handles authentication with Privy tokens and API calls.
 */

import type {
  User,
  Trader,
  CreateTraderRequest,
  TraderStatusResponse,
  TraderLogsResponse,
  SystemStats,
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Type for the Privy token getter function
type TokenGetter = () => Promise<string | null>;

class ApiClient {
  private privyTokenGetter: TokenGetter | null = null;

  /**
   * Set the Privy token getter function.
   * This should be called from the useAuth hook when it initializes.
   */
  setPrivyTokenGetter(getter: TokenGetter): void {
    this.privyTokenGetter = getter;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    
    // Add authentication header with Privy token
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };
    
    // Get Privy access token if available
    if (this.privyTokenGetter) {
      const privyToken = await this.privyTokenGetter();
      if (privyToken) {
        headers['Authorization'] = `Bearer ${privyToken}`;
      }
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    // Handle 401 Unauthorized - redirect to login
    if (response.status === 401) {
      // Privy token expired or invalid, redirect to login
      window.location.href = '/';
      throw new Error('Authentication required');
    }
    
    if (!response.ok) {
      const error = await response.json();
      
      // Handle FastAPI validation errors (422)
      if (response.status === 422) {
        // New format with errors array
        if (error.errors && Array.isArray(error.errors)) {
          const fieldErrors = error.errors.map((e: any) => 
            `${e.field}: ${e.message}`
          ).join('\n');
          throw new Error(fieldErrors);
        }
        
        // Fallback for old format
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
    
    return response.json();
  }
  
  // Auth endpoints (Privy-based)
  async me(): Promise<User> {
    return this.request<User>('/api/v1/auth/me');
  }
  
  // Trader endpoints
  async listTraders(): Promise<Trader[]> {
    return this.request<Trader[]>('/api/v1/traders');
  }
  
  async getTrader(id: string): Promise<Trader> {
    return this.request<Trader>(`/api/v1/traders/${id}`);
  }
  
  async createTrader(data: CreateTraderRequest): Promise<Trader> {
    return this.request<Trader>('/api/v1/traders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  async deleteTrader(id: string): Promise<void> {
    await this.request(`/api/v1/traders/${id}`, {
      method: 'DELETE',
    });
  }
  
  async startTrader(id: string): Promise<void> {
    await this.request(`/api/v1/traders/${id}/start`, {
      method: 'POST',
    });
  }
  
  async stopTrader(id: string): Promise<void> {
    await this.request(`/api/v1/traders/${id}/stop`, {
      method: 'POST',
    });
  }
  
  async restartTrader(id: string): Promise<void> {
    await this.request(`/api/v1/traders/${id}/restart`, {
      method: 'POST',
    });
  }
  
  async getTraderStatus(id: string): Promise<TraderStatusResponse> {
    return this.request<TraderStatusResponse>(`/api/v1/traders/${id}/status`);
  }
  
  async getTraderLogs(id: string, lines?: number): Promise<string[]> {
    const params = lines ? `?lines=${lines}` : '';
    const response = await this.request<TraderLogsResponse>(`/api/v1/traders/${id}/logs${params}`);
    return response.logs;
  }
  
  // Admin endpoints
  async adminListUsers(skip = 0, limit = 100): Promise<User[]> {
    return this.request<User[]>(`/api/v1/admin/users?skip=${skip}&limit=${limit}`);
  }
  
  async adminListTraders(skip = 0, limit = 100): Promise<Trader[]> {
    return this.request<Trader[]>(`/api/v1/admin/traders?skip=${skip}&limit=${limit}`);
  }
  
  async adminGetStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/api/v1/admin/stats');
  }
}

export const api = new ApiClient();
