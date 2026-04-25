/**
 * Sidebar and navigation component tests
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState } from '../utils/auth-helpers.js';

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
  });

  // Use desktop sidebar selector to avoid mobile/desktop duplicate elements
  const desktopSidebar = 'aside.hidden.lg\\:flex';

  test('displays HyperTrader logo', async ({ page }) => {
    // Check for brand/logo in desktop sidebar
    await expect(page.locator(desktopSidebar).getByText('HyperTrader')).toBeVisible();
  });

  test('displays navigation links', async ({ page }) => {
    // Check for navigation links in desktop sidebar (Dashboard removed; only Traders + Settings)
    await expect(page.locator(desktopSidebar).getByRole('link', { name: 'Traders' })).toBeVisible();
    await expect(page.locator(desktopSidebar).getByRole('link', { name: 'Settings' })).toBeVisible();
  });

  test('displays logout button', async ({ page }) => {
    // Check for logout button in desktop sidebar
    await expect(page.locator(desktopSidebar).getByRole('button', { name: 'Sign Out' })).toBeVisible();
  });

  test('can navigate to traders page', async ({ page }) => {
    await page.locator(desktopSidebar).getByRole('link', { name: 'Traders' }).click();
    await expect(page).toHaveURL(/\/traders/);
  });

  test('can navigate to settings page', async ({ page }) => {
    await page.locator(desktopSidebar).getByRole('link', { name: 'Settings' }).click();
    await expect(page).toHaveURL(/\/settings/);
  });

  test('logout button redirects to login', async ({ page }) => {
    // Click Sign Out - the app clears localStorage and navigates to /
    await page.locator(desktopSidebar).getByRole('button', { name: 'Sign Out' }).click();
    // Wait for redirect to complete
    await page.waitForURL('/');
    await expect(page).toHaveURL('/');
  });
});
