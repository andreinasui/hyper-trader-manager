import { test, expect } from '@playwright/test';
import { setupApiMocks, mockUser } from '../fixtures/api-handlers.js';
import { setupUnauthenticatedState, setupAuthenticatedState } from '../utils/auth-helpers.js';

test.describe('Authentication Flow', () => {
  
  test.describe('Bootstrap (First Run)', () => {
    test.beforeEach(async ({ page }) => {
      // Mock setup status as false (not initialized)
      await page.route('**/api/v1/auth/setup-status', async (route) => {
        await route.fulfill({
          status: 200,
          json: { initialized: false },
        });
      });
      
      // Mock bootstrap endpoint
      await page.route('**/api/v1/auth/bootstrap', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            json: { success: true },
          });
          return;
        }
        await route.continue();
      });
      
      // Mock login (called automatically after bootstrap)
      await page.route('**/api/v1/auth/login', async (route) => {
        if (route.request().method() === 'POST') {
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
      
      // Mock me endpoint
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          json: mockUser,
        });
      });
    });

    test('redirects to /setup when not initialized', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/');
      await expect(page).toHaveURL(/\/setup/);
    });

    test('can complete setup', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/setup');
      
      await page.getByLabel('Username').fill('admin');
      await page.getByLabel('Password', { exact: true }).fill('password123');
      await page.getByLabel('Confirm Password').fill('password123');
      
      await page.getByRole('button', { name: 'Initialize System' }).click();
      
      // Should redirect to dashboard after success
      await expect(page).toHaveURL(/\/dashboard/);
    });

    test('validates password match', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/setup');
      
      await page.getByLabel('Username').fill('admin');
      await page.getByLabel('Password', { exact: true }).fill('password123');
      await page.getByLabel('Confirm Password').fill('mismatch');
      
      await page.getByRole('button', { name: 'Initialize System' }).click();
      
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
      await expect(page).toHaveURL('/');
    });

    test('can login successfully', async ({ page }) => {
      await setupUnauthenticatedState(page);
      await page.goto('/');
      
      await page.getByLabel('Username').fill('admin');
      await page.getByLabel('Password').fill('password123');
      
      await page.getByRole('button', { name: 'Sign In' }).click();
      
      await expect(page).toHaveURL(/\/dashboard/);
    });
  });

  test.describe('Authenticated', () => {
    test.beforeEach(async ({ page }) => {
      await setupApiMocks(page);
    });

    test('redirects to dashboard if already authenticated', async ({ page }) => {
      await setupAuthenticatedState(page);
      await page.goto('/');
      await expect(page).toHaveURL(/\/dashboard/);
    });
  });
});
