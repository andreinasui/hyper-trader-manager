import { test, expect } from '@playwright/test';
import { setupApiMocks, mockUser } from '../fixtures/api-handlers.js';
import { setupUnauthenticatedState, setupAuthenticatedState } from '../utils/auth-helpers.js';

test.describe('Authentication Flow', () => {
  
  test.describe('Bootstrap (First Run)', () => {
    test.beforeEach(async ({ page }) => {
      // Track initialization state: starts false, becomes true after bootstrap
      let isInitialized = false;

      // Mock setup status - returns current initialization state
      await page.route('**/api/v1/auth/setup-status', async (route) => {
        await route.fulfill({
          status: 200,
          json: { initialized: isInitialized },
        });
      });
      
      // Mock bootstrap endpoint - returns access_token (LoginResponse format)
      await page.route('**/api/v1/auth/bootstrap', async (route) => {
        if (route.request().method() === 'POST') {
          isInitialized = true;
          await route.fulfill({
            status: 200,
            json: { 
              access_token: 'mock-bootstrap-token',
              user: mockUser,
            },
          });
          return;
        }
        await route.continue();
      });
      
      // Mock me endpoint (called after bootstrap to get user info)
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          json: mockUser,
        });
      });
      
      // Mock traders list (dashboard loads this)
      await page.route('**/api/v1/traders**', async (route) => {
        await route.fulfill({
          status: 200,
          json: { traders: [], count: 0 },
        });
      });
    });

    test('redirects to /setup when not initialized', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/\/setup/);
    });

    test('can complete setup', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/setup');
      await page.waitForLoadState('networkidle');
      
      await page.getByLabel('Admin Username').fill('admin');
      await page.getByLabel('Password', { exact: true }).fill('password123');
      await page.getByLabel('Confirm Password').fill('password123');
      
      await page.getByRole('button', { name: 'Create Admin Account' }).click();
      
      // Wait for redirect to dashboard after success
      await page.waitForURL(/\/dashboard/);
      await expect(page).toHaveURL(/\/dashboard/);
    });

    test('validates password match', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/setup');
      await page.waitForLoadState('networkidle');
      
      await page.getByLabel('Admin Username').fill('admin');
      await page.getByLabel('Password', { exact: true }).fill('password123');
      await page.getByLabel('Confirm Password').fill('mismatch');
      
      await page.getByRole('button', { name: 'Create Admin Account' }).click();
      
      await expect(page.getByText('Passwords do not match')).toBeVisible();
    });
  });

  test.describe('Login', () => {
    test.beforeEach(async ({ page }) => {
      await setupApiMocks(page); // Default mocks include initialized: true
    });

    test('redirects to login when not authenticated', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle');
      // App redirects unauthenticated users to /
      await expect(page).toHaveURL('/');
    });

    test('can login successfully', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      await page.getByLabel('Username').fill('admin');
      await page.getByLabel('Password').fill('password123');
      
      await page.getByRole('button', { name: 'Sign In' }).click();
      
      await page.waitForURL(/\/dashboard/);
      await expect(page).toHaveURL(/\/dashboard/);
    });
  });

  test.describe('Authenticated', () => {
    test.beforeEach(async ({ page }) => {
      await setupAuthenticatedState(page);
      await setupApiMocks(page);
    });

    test('redirects to dashboard if already authenticated', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/\/dashboard/);
    });
  });
});
