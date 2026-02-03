/**
 * Authentication helper utilities for Playwright tests
 */

import type { Page } from '@playwright/test';

/**
 * Mock wallet address for testing
 */
export const MOCK_WALLET_ADDRESS = '0x1234567890123456789012345678901234567890';

/**
 * Truncate wallet address for display (matches app logic in dashboard)
 * Dashboard uses: `${address.slice(0, 6)}...${address.slice(-4)}`
 * Which for 0x1234567890123456789012345678901234567890 gives: 0x1234...7890
 */
export function truncateAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

/**
 * Setup authenticated state in browser
 * This injects the mock Privy state before navigation
 */
export async function setupAuthenticatedState(page: Page) {
  await page.addInitScript(() => {
    (window as any).__PRIVY_MOCK__ = {
      enabled: true,
      authenticated: true,
      ready: true,
      user: {
        id: 'test-privy-user-id',
        linkedAccounts: [
          {
            type: 'wallet',
            address: '0x1234567890123456789012345678901234567890',
            walletClientType: 'privy',
          },
        ],
      },
    };
  });
}

/**
 * Setup unauthenticated state in browser
 */
export async function setupUnauthenticatedState(page: Page) {
  await page.addInitScript(() => {
    (window as any).__PRIVY_MOCK__ = {
      enabled: true,
      authenticated: false,
      ready: true,
      user: null,
    };
  });
}

/**
 * Wait for authentication to be ready
 */
export async function waitForAuthReady(page: Page) {
  await page.waitForFunction(() => {
    const mock = (window as any).__PRIVY_MOCK__;
    return mock && mock.ready === true;
  }, { timeout: 5000 });
}

/**
 * Simulate wallet connection (for testing login flow)
 */
export async function simulateWalletConnection(page: Page) {
  // Click connect wallet button
  await page.click('button:has-text("Connect Wallet")');
  
  // Wait for Privy modal or connection to complete
  // In mock mode, this should resolve immediately
  await page.waitForFunction(() => {
    const mock = (window as any).__PRIVY_MOCK__;
    return mock && mock.authenticated === true;
  }, { timeout: 5000 });
}

/**
 * Simulate logout
 */
export async function simulateLogout(page: Page) {
  // Click user menu
  await page.click('[data-testid="user-menu-trigger"]');
  
  // Click logout button
  await page.click('button:has-text("Logout")');
  
  // Wait for logout to complete
  await page.waitForFunction(() => {
    const mock = (window as any).__PRIVY_MOCK__;
    return mock && mock.authenticated === false;
  }, { timeout: 5000 });
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  return await page.evaluate(() => {
    const mock = (window as any).__PRIVY_MOCK__;
    return mock && mock.authenticated === true;
  });
}

/**
 * Get current mock user
 */
export async function getMockUser(page: Page) {
  return await page.evaluate(() => {
    const mock = (window as any).__PRIVY_MOCK__;
    return mock?.user || null;
  });
}
