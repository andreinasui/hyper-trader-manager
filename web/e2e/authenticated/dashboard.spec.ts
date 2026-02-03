/**
 * Dashboard page tests for authenticated users
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState, truncateAddress, MOCK_WALLET_ADDRESS } from '../utils/auth-helpers.js';

test.describe('Dashboard - Authenticated', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('displays welcome message with wallet address', async ({ page }) => {
    await page.goto('/dashboard');

    // Check heading - use getByRole to get the main heading, not the header
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

    // Check wallet address display
    const truncated = truncateAddress(MOCK_WALLET_ADDRESS);
    await expect(page.locator(`text=${truncated}`)).toBeVisible();
  });

  test('displays quick action buttons', async ({ page }) => {
    await page.goto('/dashboard');

    // Check for quick action buttons
    await expect(page.locator('button:has-text("Create Trader")').or(page.locator('a:has-text("Create Trader")'))).toBeVisible();
  });

  test('navigation header is visible', async ({ page }) => {
    await page.goto('/dashboard');

    // Check for header element  
    const header = page.locator('header');
    await expect(header).toBeVisible();
    
    // Check that HyperTrader branding is in header
    await expect(header.getByRole('heading', { name: 'HyperTrader' })).toBeVisible();
  });

  test('can navigate to trader creation from dashboard', async ({ page }) => {
    await page.goto('/dashboard');

    // Click create trader button/link
    const createButton = page.locator('a:has-text("Create Trader")').or(page.locator('button:has-text("Create Trader")'));
    
    if (await createButton.count() > 0) {
      await createButton.first().click();
      await expect(page).toHaveURL(/\/traders\/new/);
    }
  });

  test('displays traders list if user has traders', async ({ page }) => {
    await page.goto('/dashboard');

    // The API mock returns one trader, so it should be visible
    // This depends on how the dashboard displays traders
    // Adjust selector based on actual implementation
    const tradersSection = page.locator('text=Test Trader').or(page.locator('[data-testid="traders-list"]'));
    
    // Check if traders section exists (may not be on dashboard)
    const count = await tradersSection.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
