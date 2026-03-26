/**
 * Authentication helper utilities for Playwright tests
 */

import type { Page } from '@playwright/test';
import { mockUser } from '../fixtures/api-handlers.js';

/**
 * Setup authenticated state in browser
 * This sets the auth token in localStorage and mocks the auth check
 */
export async function setupAuthenticatedState(page: Page) {
  // Set token in localStorage before navigation
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'mock-test-token');
  });
}

/**
 * Setup unauthenticated state in browser
 */
export async function setupUnauthenticatedState(page: Page) {
  await page.addInitScript(() => {
    localStorage.removeItem('auth_token');
  });
}

/**
 * Wait for authentication to be ready
 */
export async function waitForAuthReady(page: Page) {
  // Wait for the auth loading spinner to disappear
  await page.waitForSelector('.animate-spin', { state: 'detached', timeout: 5000 });
}

/**
 * Simulate logout
 */
export async function simulateLogout(page: Page) {
  // Click user menu
  const userMenu = page.getByTestId('user-menu-trigger');
  if (await userMenu.isVisible()) {
    await userMenu.click();
    
    // Click logout button
    await page.getByText('Logout').click();
  }
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  return await page.evaluate(() => {
    return !!localStorage.getItem('auth_token');
  });
}

/**
 * Get current mock user
 */
export function getMockUser() {
  return mockUser;
}
