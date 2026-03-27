/**
 * API client functions for SSL setup endpoints.
 */

import { client } from '@/lib/api/client';

export interface SSLStatusResponse {
  ssl_configured: boolean;
  mode?: 'domain' | 'ip_only';
  domain?: string;
  configured_at?: string;
}

export interface SSLSetupRequest {
  mode: 'domain' | 'ip_only';
  domain?: string;
  email?: string;
}

export interface SSLSetupResponse {
  success: boolean;
  message: string;
  redirect_url?: string;
}

/**
 * Get the current SSL configuration status.
 * GET /api/v1/setup/ssl-status
 */
export async function getSSLStatus(): Promise<SSLStatusResponse> {
  const { data, error } = await client.get<SSLStatusResponse>({
    url: '/api/v1/setup/ssl-status',
  });
  if (error) {
    const err = error as { detail?: unknown };
    if (err.detail) throw new Error(JSON.stringify(err.detail));
    throw new Error(JSON.stringify(error));
  }
  return data!;
}

/**
 * Configure SSL for the application.
 * POST /api/v1/setup/ssl
 */
export async function configureSSL(request: SSLSetupRequest): Promise<SSLSetupResponse> {
  const { data, error } = await client.post<SSLSetupResponse>({
    url: '/api/v1/setup/ssl',
    body: request,
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (error) {
    const err = error as { detail?: unknown };
    if (err.detail) throw new Error(JSON.stringify(err.detail));
    throw new Error(JSON.stringify(error));
  }
  return data!;
}
