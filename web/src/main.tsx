import { StrictMode } from 'react'
import type { ReactNode } from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { PrivyProvider } from '@privy-io/react-auth'

import * as TanStackQueryProvider from './integrations/tanstack-query/root-provider.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { MockPrivyProvider } from './test/mocks/MockPrivyProvider.tsx'
import { useAuth } from './hooks/useAuth'
import { useAuthWithWalletSetup } from './hooks/useAuthWithWalletSetup'

// Import the generated route tree
import { routeTree } from './routeTree.gen'

import './styles.css'
import reportWebVitals from './reportWebVitals.ts'

// Create a new router instance with auth context type

const TanStackQueryProviderContext = TanStackQueryProvider.getContext()
const router = createRouter({
  routeTree,
  context: {
    ...TanStackQueryProviderContext,
    auth: {
      ready: false,
      authenticated: false,
      user: null,
      loading: true,
    },
  },
  defaultPreload: 'intent',
  scrollRestoration: true,
  defaultStructuralSharing: true,
  defaultPreloadStaleTime: 0,
})

// Register the router instance for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
  interface RouterContext {
    auth: {
      ready: boolean
      authenticated: boolean
      user: { walletAddress: string; privyUserId: string } | null
      loading: boolean
    }
  }
}

/**
 * AppRouter component that provides auth context to the router
 */
function AppRouter() {
  // Check if we're in mock mode (for E2E tests)
  const isMock = typeof window !== 'undefined' && !!(window as any).__PRIVY_MOCK__?.enabled
  
  // Use auto wallet setup in production, regular auth in tests
  const auth = isMock ? useAuth() : useAuthWithWalletSetup()

  return <RouterProvider router={router} context={{ auth }} />
}

/**
 * Conditionally use Mock Privy Provider for testing
 * Check for __PRIVY_MOCK__ flag set by Playwright tests
 */
function getPrivyProvider() {
  const useMock = typeof window !== 'undefined' && (window as any).__PRIVY_MOCK__?.enabled;

  if (useMock) {
    // Return a wrapper that uses MockPrivyProvider
    return ({ children }: { children: ReactNode }) => {
      const mockConfig = (window as any).__PRIVY_MOCK__;
      return (
        <MockPrivyProvider
          config={{
            authenticated: mockConfig.authenticated ?? false,
            user: mockConfig.user ?? null,
            ready: mockConfig.ready ?? true,
          }}
        >
          {children}
        </MockPrivyProvider>
      );
    };
  }

  // Return real PrivyProvider wrapper
  return ({ children }: { children: ReactNode }) => (
    <PrivyProvider
      appId={import.meta.env.VITE_PRIVY_APP_ID || ''}
      config={{
        appearance: {
          theme: 'dark',
          accentColor: '#6366f1',
          walletChainType: 'ethereum-only'
        },
        loginMethods: ['wallet'],
        embeddedWallets: {
          ethereum: {
            createOnLogin: 'all-users',
          },
          solana: {
            createOnLogin: 'off',
          },
          showWalletUIs: true,
        },
        // Arbitrum chain for Hyperliquid
        defaultChain: {
          id: 42161,
          name: 'Arbitrum One',
          network: 'arbitrum',
          nativeCurrency: {
            decimals: 18,
            name: 'Ether',
            symbol: 'ETH',
          },
          rpcUrls: {
            default: {
              http: ['https://arb1.arbitrum.io/rpc'],
            },
            public: {
              http: ['https://arb1.arbitrum.io/rpc'],
            },
          },
          blockExplorers: {
            default: { name: 'Arbiscan', url: 'https://arbiscan.io' },
          },
        },
      }}
    >
      {children}
    </PrivyProvider>
  );
}

// Render the app
const rootElement = document.getElementById('app')
if (rootElement && !rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  const AuthProvider = getPrivyProvider();

  root.render(
    <StrictMode>
      <ErrorBoundary>
        <AuthProvider>
          <TanStackQueryProvider.Provider {...TanStackQueryProviderContext}>
            <AppRouter />
          </TanStackQueryProvider.Provider>
        </AuthProvider>
      </ErrorBoundary>
    </StrictMode>,
  )
}

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals()
