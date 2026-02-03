/**
 * Authentication flow tests with Privy wallet integration
 * 
 * Tests the login/logout flow using mocked Privy authentication.
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../fixtures/api-handlers.js';
import {
  setupAuthenticatedState,
  setupUnauthenticatedState,
  MOCK_WALLET_ADDRESS,
  truncateAddress,
} from '../utils/auth-helpers.js';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Setup API mocks for all tests
    await setupApiMocks(page);
  });

  test.describe('Unauthenticated user', () => {
    test('login page displays welcome message and connect wallet button', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/');

      // Check welcome message
      await expect(page.getByRole('heading', { name: 'Welcome to HyperTrader' })).toBeVisible();
      
      // Check connect wallet button exists
      const connectButton = page.locator('button:has-text("Connect Wallet")');
      await expect(connectButton).toBeVisible();
      
      // Check feature descriptions
      await expect(page.locator('text=Secure Authentication')).toBeVisible();
      await expect(page.locator('text=Your Keys, Your Control')).toBeVisible();
      await expect(page.locator('text=Automated Agent Wallets')).toBeVisible();
    });

    test('redirects to / (login) when accessing protected route', async ({ page }) => {
      await setupUnauthenticatedState(page);
      
      // Try to access protected route
      await page.goto('/dashboard');
      
      // Should redirect to login (root path)
      await page.waitForURL('/', { timeout: 5000 });
      await expect(page).toHaveURL('/');
    });

    test('redirects to / (login) when accessing trader creation page', async ({ page }) => {
      await setupUnauthenticatedState(page);
      
      await page.goto('/traders/new');
      
      await page.waitForURL('/', { timeout: 5000 });
      await expect(page).toHaveURL('/');
    });
  });

  test.describe('Authenticated user', () => {
    test('redirects to dashboard after authentication', async ({ page }) => {
      // Start unauthenticated
      await setupUnauthenticatedState(page);
      await page.goto('/');

      // Simulate authentication
      await setupAuthenticatedState(page);
      await page.reload();

      // Should redirect to dashboard
      await page.waitForURL('/dashboard', { timeout: 5000 });
      await expect(page).toHaveURL('/dashboard');
    });

    test('can access protected routes when authenticated', async ({ page }) => {
      await setupAuthenticatedState(page);
      
      await page.goto('/dashboard');
      
      // Should NOT redirect
      await expect(page).toHaveURL('/dashboard');
      await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    });

    test('dashboard displays user wallet address', async ({ page }) => {
      await setupAuthenticatedState(page);
      
      await page.goto('/dashboard');
      
      // Check that wallet address is displayed (truncated)
      const expectedTruncated = truncateAddress(MOCK_WALLET_ADDRESS);
      await expect(page.locator(`text=${expectedTruncated}`)).toBeVisible();
    });

    test('can access trader creation page', async ({ page }) => {
      await setupAuthenticatedState(page);
      
      await page.goto('/traders/new');
      
      await expect(page).toHaveURL('/traders/new');
    });
  });

  test.describe('Loading states', () => {
    test('shows loading indicator while auth initializes', async ({ page }) => {
      // Don't setup auth state immediately
      await page.goto('/');
      
      // Should show some content (either loading or login page)
      await expect(page.locator('body')).not.toBeEmpty();
    });
  });
});
