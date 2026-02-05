/**
 * Mock Privy Provider for Testing
 * 
 * Replaces the real PrivyProvider in tests to avoid real wallet connections.
 * Provides a controllable authentication state for E2E and component tests.
 */

import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';

// Mock user structure matching Privy's user object
export interface MockPrivyUser {
  id: string;
  wallet?: {
    address: string;
  };
  linkedAccounts?: Array<{
    type: string;
    address: string;
    walletClientType?: string;
  }>;
}

export interface MockPrivyConfig {
  authenticated?: boolean;
  user?: MockPrivyUser;
  ready?: boolean;
}

interface PrivyContextValue {
  ready: boolean;
  authenticated: boolean;
  user: MockPrivyUser | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

// Create context using the same module path as real Privy to override it
const MockPrivyContext = createContext<PrivyContextValue | null>(null);

/**
 * Default mock user for testing
 */
export const createMockPrivyUser = (overrides?: Partial<MockPrivyUser>): MockPrivyUser => ({
  id: 'test-privy-user-id',
  wallet: {
    address: '0x1234567890123456789012345678901234567890',
  },
  linkedAccounts: [
    {
      type: 'wallet',
      address: '0x1234567890123456789012345678901234567890',
      walletClientType: 'metamask', // External wallet
    },
  ],
  ...overrides,
});

/**
 * Mock Privy Provider Component
 * 
 * Usage in tests:
 * ```tsx
 * <MockPrivyProvider config={{ authenticated: true }}>
 *   <App />
 * </MockPrivyProvider>
 * ```
 */
export function MockPrivyProvider({
  children,
  config = {},
}: {
  children: ReactNode;
  config?: MockPrivyConfig;
}) {
  const [ready] = useState(config.ready ?? true);
  const [authenticated, setAuthenticated] = useState(config.authenticated ?? false);
  const [user, setUser] = useState<MockPrivyUser | null>(
    config.authenticated ? (config.user || createMockPrivyUser()) : null
  );

  const login = useCallback(async () => {
    // Simulate async login
    await new Promise(resolve => setTimeout(resolve, 100));
    const mockUser = createMockPrivyUser();
    setUser(mockUser);
    setAuthenticated(true);
  }, []);

  const logout = useCallback(async () => {
    // Simulate async logout
    await new Promise(resolve => setTimeout(resolve, 50));
    setUser(null);
    setAuthenticated(false);
  }, []);

  const getAccessToken = useCallback(async (): Promise<string | null> => {
    if (!authenticated) return null;
    // Return a mock JWT token
    return 'mock-privy-access-token';
  }, [authenticated]);

  const value: PrivyContextValue = {
    ready,
    authenticated,
    user,
    login,
    logout,
    getAccessToken,
  };

  return (
    <MockPrivyContext.Provider value={value}>
      {children}
    </MockPrivyContext.Provider>
  );
}

/**
 * Hook to access mock Privy context in tests
 * This is exported as a named export that can replace usePrivy from @privy-io/react-auth
 */
export function usePrivy(): PrivyContextValue {
  const context = useContext(MockPrivyContext);
  if (!context) {
    throw new Error('usePrivy must be used within MockPrivyProvider');
  }
  return context;
}

// Also export as useMockPrivy for backwards compatibility
export const useMockPrivy = usePrivy;

/**
 * Test utilities for setting up auth state
 */
export const mockAuthUtils = {
  /**
   * Get URL param to control mock auth state
   */
  getAuthParam: (authenticated: boolean) => 
    `?mock-auth=${authenticated ? 'true' : 'false'}`,
  
  /**
   * Check if we should use mock auth from URL params
   */
  shouldUseMockAuth: () => {
    if (typeof window === 'undefined') return false;
    const params = new URLSearchParams(window.location.search);
    return params.has('mock-auth');
  },
  
  /**
   * Get mock auth state from URL params
   */
  getMockAuthState: (): boolean => {
    if (typeof window === 'undefined') return false;
    const params = new URLSearchParams(window.location.search);
    return params.get('mock-auth') === 'true';
  },
};
