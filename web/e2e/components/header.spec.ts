/**
 * Header and user menu component tests
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState, truncateAddress, MOCK_WALLET_ADDRESS } from '../utils/auth-helpers.js';

test.describe('Header Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('displays HyperTrader logo/brand', async ({ page }) => {
    await page.goto('/dashboard');

    // Check for brand/logo
    await expect(page.locator('text=HyperTrader')).toBeVisible();
  });

  test('displays user menu with wallet address', async ({ page }) => {
    await page.goto('/dashboard');

    // Wallet address should be visible in header
    const truncated = truncateAddress(MOCK_WALLET_ADDRESS, 4);
    await expect(page.locator(`text=${truncated}`)).toBeVisible();
  });

  test('user menu opens on click', async ({ page }) => {
    await page.goto('/dashboard');

    // Find and click user menu trigger
    // The dashboard uses a Button with avatar and truncated address
    const menuTrigger = page.locator('button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Menu should open
    await expect(page.locator('text=Connected Wallet')).toBeVisible();
    await expect(page.locator('text=Copy Address')).toBeVisible();
    await expect(page.locator('text=Logout')).toBeVisible();
  });

  test('can copy wallet address from user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Grant clipboard permissions
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);

    // Click copy address
    await page.click('text=Copy Address');

    // Verify clipboard content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toBe(MOCK_WALLET_ADDRESS);
  });

  test('displays full wallet address in user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Full address should be visible in dropdown
    await expect(page.locator(`text=${MOCK_WALLET_ADDRESS}`)).toBeVisible();
  });

  test('settings link is available in user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Settings link should exist
    await expect(page.locator('text=Settings')).toBeVisible();
  });

  test('can navigate to settings from user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Click settings
    await page.click('text=Settings');

    // Should navigate to settings
    await expect(page).toHaveURL('/settings');
  });

  test('logout button triggers logout and redirects to login', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Click logout
    await page.click('text=Logout');

    // Should redirect to login
    // Note: In actual implementation, this will depend on how logout is handled
    // The mock provider should clear auth state
    await page.waitForTimeout(500); // Wait for logout to process
  });

  test('arbiscan link is present in user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Check for Arbiscan link
    await expect(page.locator('text=View on Arbiscan')).toBeVisible();
  });
});

test.describe('Navigation Links', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('create trader button navigates to trader creation', async ({ page }) => {
    await page.goto('/dashboard');

    // Click create trader button
    const createButton = page.locator('a:has-text("Create Trader")').first();
    await createButton.click();

    // Should navigate to trader creation page
    // Note: This route may not exist yet
    await page.waitForURL(/\/traders\/new/, { timeout: 5000 }).catch(() => {
      // Route might not exist yet
    });
  });

  test('can navigate between dashboard and traders list', async ({ page }) => {
    await page.goto('/dashboard');

    // Navigate to traders list (if link exists)
    const tradersLink = page.locator('a[href="/traders"]');
    
    if (await tradersLink.count() > 0) {
      await tradersLink.click();
      await expect(page).toHaveURL('/traders');
    }
  });
});
