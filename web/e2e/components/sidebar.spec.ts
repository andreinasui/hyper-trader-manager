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
  });

  test('displays HyperTrader logo', async ({ page }) => {
    // Check for brand/logo
    await expect(page.locator('aside').getByText('HyperTrader')).toBeVisible();
  });

  test('displays navigation links', async ({ page }) => {
    // Check for navigation links
    await expect(page.locator('aside a[href="/dashboard"]')).toBeVisible();
    await expect(page.locator('aside a[href="/traders"]')).toBeVisible();
    await expect(page.locator('aside a[href="/settings"]')).toBeVisible();
  });

  test('displays logout button', async ({ page }) => {
    // Check for logout button
    await expect(page.getByRole('button', { name: 'Disconnect' })).toBeVisible();
  });

  test('can navigate to traders page', async ({ page }) => {
    await page.locator('aside a[href="/traders"]').click();
    await expect(page).toHaveURL(/\/traders/);
  });

  test('can navigate to settings page', async ({ page }) => {
    await page.locator('aside a[href="/settings"]').click();
    await expect(page).toHaveURL(/\/settings/);
  });

  test('logout button redirects to login', async ({ page }) => {
    await page.getByRole('button', { name: 'Disconnect' }).click();
    await expect(page).toHaveURL('/');
  });
});
