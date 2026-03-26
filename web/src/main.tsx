import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'

import * as TanStackQueryProvider from './integrations/tanstack-query/root-provider.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { AuthProvider, useAuth, type AuthUser } from './hooks/useAuth'

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
      isInitialized: false,
      token: null,
      login: async () => {},
      logout: () => {},
      bootstrap: async () => {},
      checkAuth: async () => {},
      checkSetup: async () => {},
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
      user: AuthUser | null
      loading: boolean
      isInitialized: boolean
      token: string | null
      login: (username: string, password: string) => Promise<void>
      logout: () => void
      bootstrap: (username: string, password: string) => Promise<void>
      checkAuth: () => Promise<void>
      checkSetup: () => Promise<void>
    }
  }
}

/**
 * AppRouter component that provides auth context to the router
 */
function AppRouter() {
  const auth = useAuth()
  return <RouterProvider router={router} context={{ auth }} />
}

// Render the app
const rootElement = document.getElementById('app')
if (rootElement && !rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)

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
