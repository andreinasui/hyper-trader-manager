/**
 * Playwright fixtures for mocking Privy authentication
 * 
 * Provides reusable page fixtures with different authentication states.
 */

import { test as base } from '@playwright/test';
import type { Page } from '@playwright/test';
import type { MockPrivyUser } from '../../src/test/mocks/MockPrivyProvider.js';

export interface AuthFixtures {
  authenticatedPage: Page;
  unauthenticatedPage: Page;
  mockUser: MockPrivyUser;
}

/**
 * Default mock user data
 */
export const createMockUser = (overrides?: Partial<MockPrivyUser>): MockPrivyUser => ({
  id: 'test-privy-user-id',
  wallet: {
    address: '0x1234567890123456789012345678901234567890',
  },
  linkedAccounts: [
    {
      type: 'wallet',
      address: '0x1234567890123456789012345678901234567890',
      walletClientType: 'metamask',
    },
  ],
  ...overrides,
});

/**
 * Setup Privy mock in browser context
 */
async function setupPrivyMock(page: Page, authenticated: boolean, user?: MockPrivyUser) {
  // Inject mock before page loads
  await page.addInitScript(({ authenticated, user }) => {
    // Store mock auth state in window for app to read
    (window as any).__PRIVY_MOCK__ = {
      enabled: true,
      authenticated,
      user: authenticated ? user : null,
      ready: true,
    };
  }, { authenticated, user: authenticated ? (user || createMockUser()) : null });
}

/**
 * Extended Playwright test with auth fixtures
 */
export const test = base.extend<AuthFixtures>({
  /**
   * Page fixture with authenticated state
   */
  authenticatedPage: async ({ page }, use) => {
    const mockUser = createMockUser();
    await setupPrivyMock(page, true, mockUser);
    await use(page);
  },

  /**
   * Page fixture with unauthenticated state
   */
  unauthenticatedPage: async ({ page }, use) => {
    await setupPrivyMock(page, false);
    await use(page);
  },

  /**
   * Mock user data fixture
   */
  mockUser: async ({}, use) => {
    await use(createMockUser());
  },
});

export { expect } from '@playwright/test';
