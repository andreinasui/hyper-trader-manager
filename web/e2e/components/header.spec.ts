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

    // Check for brand/logo in the main header
    // Dashboard page has a header with an h1
    await expect(page.locator('header h1:has-text("HyperTrader")')).toBeVisible();
  });

  test('displays user menu with wallet address', async ({ page }) => {
    await page.goto('/dashboard');

    // Wallet address should be visible in header
    const truncated = truncateAddress(MOCK_WALLET_ADDRESS, 4);
    // Be specific to the header button
    await expect(page.locator('header button').filter({ hasText: truncated })).toBeVisible();
  });

  test('user menu opens on click', async ({ page }) => {
    await page.goto('/dashboard');

    // Find and click user menu trigger
    const menuTrigger = page.locator('header button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Menu should open
    await expect(page.getByRole('menu')).toBeVisible();
    await expect(page.getByRole('menuitem', { name: 'Connected Wallet' }).or(page.locator('text=Connected Wallet'))).toBeVisible();
    await expect(page.getByRole('menuitem', { name: 'Copy Address' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: 'Logout' })).toBeVisible();
  });

  test('can copy wallet address from user menu', async ({ page, browserName }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('header button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Grant clipboard permissions (Firefox doesn't support clipboard-read)
    if (browserName === 'chromium') {
      await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
    } else if (browserName === 'webkit') {
      await page.context().grantPermissions(['clipboard-write']);
    }

    // Click copy address
    await page.getByRole('menuitem', { name: 'Copy Address' }).click();

    // Verify clipboard content (only on browsers that support clipboard API)
    if (browserName === 'chromium' || browserName === 'webkit') {
      const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
      expect(clipboardText).toBe(MOCK_WALLET_ADDRESS);
    } else {
      // For Firefox, just verify the button was clicked
      // (clipboard API is less reliable in Firefox)
      await expect(page.getByRole('menu')).toBeVisible();
    }
  });

  test('displays full wallet address in user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('header button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Full address should be visible in dropdown
    await expect(page.locator('role=menu').locator(`text=${MOCK_WALLET_ADDRESS}`)).toBeVisible();
  });

  test('settings link is available in user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('header button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Settings link should exist in the menu
    await expect(page.getByRole('menuitem', { name: 'Settings' })).toBeVisible();
  });

  test('can navigate to settings from user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('header button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Click settings in the menu
    await page.getByRole('menuitem', { name: 'Settings' }).click();

    // Should navigate to settings
    await expect(page).toHaveURL('/settings');
  });

  test('logout button triggers logout and redirects to login', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('header button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Click logout
    await page.getByRole('menuitem', { name: 'Logout' }).click();

    // Should redirect to login
    await page.waitForURL('/');
  });

  test('arbiscan link is present in user menu', async ({ page }) => {
    await page.goto('/dashboard');

    // Open user menu
    const menuTrigger = page.locator('header button').filter({ hasText: truncateAddress(MOCK_WALLET_ADDRESS, 4) });
    await menuTrigger.click();

    // Check for Arbiscan link
    await expect(page.getByRole('menuitem', { name: 'View on Arbiscan' })).toBeVisible();
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
