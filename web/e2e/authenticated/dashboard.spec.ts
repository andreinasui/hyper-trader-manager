/**
 * Dashboard page tests for authenticated users
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks, mockUser } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState } from '../utils/auth-helpers.js';

test.describe('Dashboard - Authenticated', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('displays dashboard heading and description', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Check main dashboard heading
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    
    // Check description text
    await expect(page.getByText('Manage your trading bots')).toBeVisible();
  });

  test('displays New Trader button in header', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // The main "New Trader" button is in the header area (not sidebar)
    // Use the button specifically (the link might be in sidebar)
    await expect(page.getByRole('button', { name: /New Trader/i })).toBeVisible();
  });

  test('shows sidebar navigation', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Check sidebar navigation items exist (they may be in a complementary/aside role)
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Traders' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible();
  });

  test('can navigate to trader creation from dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Click the main "New Trader" button in the header
    await page.getByRole('button', { name: /New Trader/i }).click();
    await expect(page).toHaveURL(/\/traders\/new/);
  });

  test('displays traders list if user has traders', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // The API mock returns one trader named "Test Trader"
    await expect(page.getByText('Test Trader')).toBeVisible();
    
    // Should show running status
    await expect(page.getByText('running')).toBeVisible();
  });
});
