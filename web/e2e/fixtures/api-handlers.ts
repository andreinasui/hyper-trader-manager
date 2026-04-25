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
  username: 'admin',
  is_admin: true,
  created_at: '2024-01-01T00:00:00Z',
};

/**
 * Mock trader data
 */
export const mockTrader: Trader = {
  id: 'test-trader-id',
  user_id: 'test-user-id',
  name: 'Test Trader',
  description: 'A test trading bot',
  wallet_address: '0x1234567890123456789012345678901234567890',
  runtime_name: 'trader-12345678',
  status: 'running',
  image_tag: 'latest',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  start_attempts: 1,
  last_error: null,
  stopped_at: null,
  display_name: 'Test Trader',
  latest_config: {
    provider_settings: {
      exchange: 'hyperliquid',
      network: 'mainnet',
      self_account: {
        address: '0x1234567890123456789012345678901234567890',
        is_sub: false,
      },
      copy_account: {
        address: '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
      },
    },
    trader_settings: {
      trading_strategy: {
        type: 'order_based',
        risk_parameters: {
          blocked_assets: [],
          self_proportionality_multiplier: 1.0,
          open_on_low_pnl: {
            enabled: true,
            max_pnl: 0.05,
          },
        },
      },
    },
  },
};

/**
 * Setup API route mocking
 */
export async function setupApiMocks(page: Page) {
  // Mock auth setup status (default to initialized)
  await page.route('**/api/v1/auth/setup-status', async (route) => {
    await route.fulfill({
      status: 200,
      json: { initialized: true },
    });
  });

  // Mock login
  await page.route('**/api/v1/auth/login', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        json: {
          access_token: 'mock-access-token',
          user: mockUser,
        },
      });
      return;
    }
    await route.continue();
  });
  
  // Mock bootstrap
  await page.route('**/api/v1/auth/bootstrap', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        json: {
          success: true,
        },
      });
      return;
    }
    await route.continue();
  });

  // Mock logout
  await page.route('**/api/v1/auth/logout', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        json: { success: true },
      });
      return;
    }
    await route.continue();
  });

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

  // Mock traders list - be permissive with trailing slashes
  await page.route(url => url.pathname.includes('/api/v1/traders'), async (route) => {
    const url = route.request().url();
    const method = route.request().method();
    
    // Base list or create endpoint
    if (url.match(/\/api\/v1\/traders\/?(\?.*)?$/)) {
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          json: {
            traders: [mockTrader],
            count: 1
          },
        });
        return;
      } else if (method === 'POST') {
        const body = route.request().postDataJSON() as CreateTraderRequest;
        
        // Validate request - only config.name is required in v1
        const errors: any[] = [];
        
        if (!body.config?.name) {
          errors.push({ 
            field: 'config.name', 
            message: 'Trader name is required' 
          });
        }
        
        if (errors.length > 0) {
          await route.fulfill({
            status: 422,
            json: { detail: errors },
          });
          return;
        }
        
        // Create new trader
        const newTrader: Trader = {
          ...mockTrader,
          id: `trader-${Date.now()}`,
          wallet_address: body.wallet_address || '0x0000000000000000000000000000000000000000',
          latest_config: body.config,
          status: 'configured',
        };
        
        await route.fulfill({
          status: 201,
          json: newTrader,
        });
        return;
      }
    }
    
    // Sub-resources (e.g., /api/v1/traders/{id}/status)
    if (url.match(/\/api\/v1\/traders\/[^\/]+\/status\/?$/)) {
      await route.fulfill({
        status: 200,
        json: {
          id: mockTrader.id,
          wallet_address: mockTrader.wallet_address,
          runtime_name: mockTrader.runtime_name,
          status: 'running',
          runtime_status: {
            state: 'running',
            running: true,
            started_at: '2024-01-01T00:00:00Z',
          },
        },
      });
      return;
    }

    if (url.match(/\/api\/v1\/traders\/[^\/]+\/logs\/?/)) {
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
      return;
    }

    // Single trader detail
    if (url.match(/\/api\/v1\/traders\/[^\/]+\/?$/)) {
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          json: mockTrader,
        });
      } else if (method === 'DELETE') {
        await route.fulfill({
          status: 204,
          json: { success: true },
        });
      } else if (method === 'PATCH') {
        // Update trader info (name/description)
        const body = route.request().postDataJSON();
        const updatedTrader = {
          ...mockTrader,
          ...body,
          updated_at: new Date().toISOString(),
        };
        await route.fulfill({
          status: 200,
          json: updatedTrader,
        });
      }
      return;
    }

    // Config update endpoint
    if (url.match(/\/api\/v1\/traders\/[^\/]+\/config\/?$/)) {
      if (method === 'PATCH') {
        const body = route.request().postDataJSON();
        const updatedTrader = {
          ...mockTrader,
          latest_config: body.config,
          updated_at: new Date().toISOString(),
        };
        await route.fulfill({
          status: 200,
          json: updatedTrader,
        });
      }
      return;
    }

    // Control endpoints
    if (url.match(/\/api\/v1\/traders\/[^\/]+\/start\/?$/)) {
      await route.fulfill({
        status: 200,
        json: {
          message: 'Trader started successfully',
          trader_id: mockTrader.id,
          runtime_name: mockTrader.runtime_name,
          status: 'running',
          start_attempts: mockTrader.start_attempts + 1,
        },
      });
      return;
    }

    if (url.match(/\/api\/v1\/traders\/[^\/]+\/stop\/?$/)) {
      await route.fulfill({
        status: 200,
        json: {
          message: 'Trader stopped successfully',
          trader_id: mockTrader.id,
          runtime_name: mockTrader.runtime_name,
          status: 'stopped',
        },
      });
      return;
    }

    if (url.match(/\/api\/v1\/traders\/[^\/]+\/restart\/?$/)) {
      await route.fulfill({
        status: 200,
        json: {
          message: 'Trader restarted successfully',
          trader_id: mockTrader.id,
          runtime_name: mockTrader.runtime_name,
          status: 'running',
          start_attempts: mockTrader.start_attempts + 1,
        },
      });
      return;
    }

    await route.continue();
  });
}

/**
 * Setup API error responses for testing error handling
 */
export async function setupApiErrors(page: Page) {
  // Set up standard auth mocks so authenticated routes work
  await setupApiMocks(page);

  // Override traders POST to return a server error (registered after setupApiMocks, so takes priority)
  await page.route(url => url.pathname.match(/\/api\/v1\/traders\/?$/) !== null, async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 500,
        json: { detail: 'Internal server error' },
      });
      return;
    }
    await route.continue();
  });
}
