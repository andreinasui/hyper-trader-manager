/**
 * Test wrapper component for component tests
 * 
 * Wraps components with necessary providers for testing.
 */

import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MockPrivyProvider } from '../../src/test/mocks/MockPrivyProvider.js';
import type { MockPrivyConfig } from '../../src/test/mocks/MockPrivyProvider.js';

interface TestWrapperProps {
  children: ReactNode;
  privyConfig?: MockPrivyConfig;
}

/**
 * Create a test QueryClient with sensible defaults
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * Test wrapper component
 * 
 * Usage:
 * ```tsx
 * import { render } from '@testing-library/react';
 * import { TestWrapper } from './utils/test-wrapper';
 * 
 * render(
 *   <TestWrapper privyConfig={{ authenticated: true }}>
 *     <YourComponent />
 *   </TestWrapper>
 * );
 * ```
 */
export function TestWrapper({ children, privyConfig = {} }: TestWrapperProps) {
  const queryClient = createTestQueryClient();

  return (
    <MockPrivyProvider config={privyConfig}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </MockPrivyProvider>
  );
}

/**
 * Authenticated test wrapper
 */
export function AuthenticatedTestWrapper({ children }: { children: ReactNode }) {
  return (
    <TestWrapper privyConfig={{ authenticated: true }}>
      {children}
    </TestWrapper>
  );
}

/**
 * Unauthenticated test wrapper
 */
export function UnauthenticatedTestWrapper({ children }: { children: ReactNode }) {
  return (
    <TestWrapper privyConfig={{ authenticated: false }}>
      {children}
    </TestWrapper>
  );
}
