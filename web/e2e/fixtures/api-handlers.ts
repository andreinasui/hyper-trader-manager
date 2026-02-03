/**
 * Mock API handlers for Playwright tests
 * 
 * Intercepts API calls and returns mock responses.
 */

import type { Page } from '@playwright/test';
import type { User, Trader, CreateTraderRequest } from '../../src/lib/types.js';

/**
 * Mock user data matching backend User schema
 */
export const mockUser: User = {
  id: 'test-user-id',
  privy_user_id: 'test-privy-user-id',
  wallet_address: '0x1234567890123456789012345678901234567890',
  created_at: '2024-01-01T00:00:00Z',
};

/**
 * Mock trader data
 */
export const mockTrader: Trader = {
  id: 'test-trader-id',
  user_id: 'test-user-id',
  name: 'Test Trader',
  wallet_address: '0x1234567890123456789012345678901234567890',
  agent_address: '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
  k8s_name: 'trader-12345678',
  status: 'running',
  image_tag: 'latest',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  latest_config: {
    name: 'Test Trader',
    exchange: 'hyperliquid',
    self_account: {
      address: '0x1234567890123456789012345678901234567890',
      base_url: 'testnet',
    },
    copy_account: {
      address: '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
      base_url: 'testnet',
    },
  },
};

/**
 * Setup API route mocking
 */
export async function setupApiMocks(page: Page) {
  // Mock auth endpoints
  await page.route('**/api/v1/auth/me', async (route) => {
    const authHeader = route.request().headers()['authorization'];
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      await route.fulfill({
        status: 401,
        json: { detail: 'Authentication required' },
      });
      return;
    }

    await route.fulfill({
      status: 200,
      json: mockUser,
    });
  });

  // Mock traders list
  await page.route('**/api/v1/traders', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        json: [mockTrader],
      });
    } else if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as CreateTraderRequest;
      
      // Validate request
      const errors: any[] = [];
      
      if (!body.wallet_address) {
        errors.push({ 
          field: 'wallet_address', 
          message: 'Field required' 
        });
      }
      
      if (!body.config?.name) {
        errors.push({ 
          field: 'config.name', 
          message: 'Trader name is required' 
        });
      }
      
      if (errors.length > 0) {
        await route.fulfill({
          status: 422,
          json: { errors },
        });
        return;
      }
      
      // Create new trader
      const newTrader: Trader = {
        ...mockTrader,
        id: `trader-${Date.now()}`,
        wallet_address: body.wallet_address,
        latest_config: body.config,
        status: 'pending',
      };
      
      await route.fulfill({
        status: 201,
        json: newTrader,
      });
    }
  });

  // Mock single trader detail
  await page.route('**/api/v1/traders/*', async (route) => {
    const method = route.request().method();
    
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        json: mockTrader,
      });
    } else if (method === 'DELETE') {
      await route.fulfill({
        status: 204,
      });
    }
  });

  // Mock trader control endpoints
  await page.route('**/api/v1/traders/*/start', async (route) => {
    await route.fulfill({ status: 200, json: {} });
  });

  await page.route('**/api/v1/traders/*/stop', async (route) => {
    await route.fulfill({ status: 200, json: {} });
  });

  await page.route('**/api/v1/traders/*/restart', async (route) => {
    await route.fulfill({ status: 200, json: {} });
  });

  // Mock trader status
  await page.route('**/api/v1/traders/*/status', async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        id: mockTrader.id,
        wallet_address: mockTrader.wallet_address,
        k8s_name: mockTrader.k8s_name,
        status: 'running',
        k8s_status: {
          pod_phase: 'Running',
          ready: true,
          restarts: 0,
          pod_ip: '10.0.0.1',
          node: 'node-1',
          started_at: '2024-01-01T00:00:00Z',
        },
      },
    });
  });

  // Mock trader logs
  await page.route('**/api/v1/traders/*/logs*', async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        trader_id: mockTrader.id,
        logs: [
          '[2024-01-01 00:00:00] Trader started',
          '[2024-01-01 00:01:00] Connected to exchange',
          '[2024-01-01 00:02:00] Monitoring positions',
        ],
        total_lines: 3,
      },
    });
  });
}

/**
 * Setup API error responses for testing error handling
 */
export async function setupApiErrors(page: Page) {
  await page.route('**/api/v1/traders', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 500,
        json: { detail: 'Internal server error' },
      });
    }
  });
}
