/**
 * Trader lifecycle E2E tests
 * 
 * Tests start/stop actions for traders from both list and detail views.
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks, mockTrader } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState } from '../utils/auth-helpers.js';
import type { Trader } from '../../src/lib/types.js';

test.describe('Trader Lifecycle - Start/Stop Actions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('can start a stopped trader from list', async ({ page }) => {
    // Override mock to return stopped trader
    const stoppedTrader: Trader = {
      ...mockTrader,
      status: 'stopped',
      stopped_at: '2024-01-01T00:00:00Z',
    };

    let startCalled = false;

    // Handle traders list AND start endpoint
    await page.route('**/api/v1/traders**', async (route) => {
      const url = route.request().url();
      const method = route.request().method();

      // Start endpoint
      if (url.includes('/start') && method === 'POST') {
        startCalled = true;
        await route.fulfill({
          status: 200,
          json: {
            message: 'Trader started successfully',
            trader_id: stoppedTrader.id,
            status: 'running',
          },
        });
        return;
      }

      // Traders list
      if (url.match(/\/api\/v1\/traders\/?(\?.*)?$/)) {
        if (method === 'GET') {
          await route.fulfill({
            status: 200,
            json: {
              traders: [stoppedTrader],
              count: 1,
            },
          });
          return;
        }
      }

      await route.continue();
    });

    // Navigate to traders list
    await page.goto('/traders', { waitUntil: 'networkidle' });

    // Wait for page to load - use getByRole for better accessibility
    await expect(page.getByRole('heading', { name: 'Traders' })).toBeVisible();

    // Find the start button (Play icon)
    const startButton = page.locator('button[title="Start"]').first();
    await expect(startButton).toBeVisible();

    // Click start button
    await startButton.click();

    // Verify start was called
    await page.waitForTimeout(500);
    expect(startCalled).toBe(true);
  });

  test('can stop a running trader from list', async ({ page }) => {
    let stopCalled = false;

    // Handle stop endpoint
    await page.route('**/api/v1/traders/**/stop', async (route) => {
      if (route.request().method() === 'POST') {
        stopCalled = true;
        await route.fulfill({
          status: 200,
          json: {
            message: 'Trader stopped successfully',
            trader_id: mockTrader.id,
            status: 'stopped',
          },
        });
        return;
      }
      await route.continue();
    });

    // Navigate to traders list (mockTrader is already running by default)
    await page.goto('/traders', { waitUntil: 'networkidle' });

    // Wait for page to load
    await expect(page.getByRole('heading', { name: 'Traders' })).toBeVisible();

    // Find the stop button (Square icon)
    const stopButton = page.locator('button[title="Stop"]').first();
    await expect(stopButton).toBeVisible();

    // Click stop button
    await stopButton.click();

    // Verify stop was called
    await page.waitForTimeout(500);
    expect(stopCalled).toBe(true);
  });

  test('displays trader status correctly', async ({ page }) => {
    // Navigate to traders list
    await page.goto('/traders', { waitUntil: 'networkidle' });

    // Wait for list to load (div-based rows, no table)
    await expect(page.getByRole('heading', { name: 'Traders' })).toBeVisible();

    // Check that status indicator is visible
    const statusIndicator = page.getByText(/running/i).first();
    await expect(statusIndicator).toBeVisible();
  });
});

test.describe('Trader Detail - Lifecycle Actions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('shows start/stop button based on trader status', async ({ page }) => {
    // Navigate to trader detail page (mockTrader is running by default)
    await page.goto(`/traders/${mockTrader.id}`, { waitUntil: 'networkidle' });

    // Wait for page to load - use display_name from mockTrader
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Running trader should have a stop button
    const stopButton = page.getByRole('button', { name: 'Stop', exact: true });
    await expect(stopButton).toBeVisible();

    // Should NOT have a start button (running traders can't be started)
    // Use exact: true to avoid matching "Restart"
    const startButton = page.getByRole('button', { name: 'Start', exact: true });
    await expect(startButton).not.toBeVisible();
  });

  test('shows error state when start fails', async ({ page }) => {
    // Override mock to return failed trader with error message
    const failedTrader: Trader = {
      ...mockTrader,
      status: 'failed',
      last_error: 'Failed to connect to exchange: Connection timeout',
    };

    // Handle both GET (for trader data) and other requests
    await page.route(`**/api/v1/traders/${mockTrader.id}`, async (route) => {
      const method = route.request().method();
      
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          json: failedTrader,
        });
        return;
      }
      
      // For start requests, return success
      await route.fulfill({
        status: 200,
        json: { message: 'ok' },
      });
    });

    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`, { waitUntil: 'networkidle' });

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Should display failed status badge
    const statusBadge = page.locator('text=/failed/i').first();
    await expect(statusBadge).toBeVisible();

    // Should display error message in the status card
    const errorText = page.locator('text=/Failed to connect to exchange/i');
    await expect(errorText).toBeVisible();

    // Should show retry button (for failed traders)
    const retryButton = page.locator('button:has-text("Retry")').first();
    await expect(retryButton).toBeVisible();
  });

  test('can start a configured trader from detail page', async ({ page }) => {
    // Override mock to return configured trader (never started)
    const configuredTrader: Trader = {
      ...mockTrader,
      status: 'configured',
      start_attempts: 0,
    };

    let startCalled = false;

    // Handle both GET (for trader data) and POST (for start)
    await page.route(`**/api/v1/traders/${mockTrader.id}**`, async (route) => {
      const url = route.request().url();
      const method = route.request().method();
      
      // Start endpoint
      if (url.includes('/start') && method === 'POST') {
        startCalled = true;
        await route.fulfill({
          status: 200,
          json: {
            message: 'Trader started successfully',
            trader_id: configuredTrader.id,
            status: 'running',
          },
        });
        return;
      }
      
      // Trader detail GET
      if (method === 'GET' && !url.includes('/status') && !url.includes('/logs')) {
        await route.fulfill({
          status: 200,
          json: configuredTrader,
        });
        return;
      }
      
      await route.continue();
    });

    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`, { waitUntil: 'networkidle' });

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Should show start button
    const startButton = page.locator('button:has-text("Start")').first();
    await expect(startButton).toBeVisible();

    // Click start button
    await startButton.click();

    // Verify start was called
    await page.waitForTimeout(500);
    expect(startCalled).toBe(true);
  });

  test('can stop a running trader from detail page', async ({ page }) => {
    let stopCalled = false;

    // Handle stop endpoint
    await page.route(`**/api/v1/traders/${mockTrader.id}/stop`, async (route) => {
      if (route.request().method() === 'POST') {
        stopCalled = true;
        await route.fulfill({
          status: 200,
          json: {
            message: 'Trader stopped successfully',
            trader_id: mockTrader.id,
            status: 'stopped',
          },
        });
        return;
      }
      await route.continue();
    });

    // Navigate to trader detail page (mockTrader is running by default)
    await page.goto(`/traders/${mockTrader.id}`, { waitUntil: 'networkidle' });

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Should show stop button
    const stopButton = page.locator('button:has-text("Stop")').first();
    await expect(stopButton).toBeVisible();

    // Click stop button
    await stopButton.click();

    // Verify stop was called
    await page.waitForTimeout(500);
    expect(stopCalled).toBe(true);
  });
});
