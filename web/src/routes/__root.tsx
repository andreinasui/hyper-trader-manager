import { Outlet, createRootRouteWithContext } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'

import TanStackQueryDevtools from '../integrations/tanstack-query/devtools'

import type { QueryClient } from '@tanstack/react-query'
import type { AuthUser } from '@/hooks/useAuth'

interface MyRouterContext {
  queryClient: QueryClient
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

export const Route = createRootRouteWithContext<MyRouterContext>()({
  component: RootComponent,
})

function RootComponent() {
  return (
    <>
      <Outlet />
      <TanStackDevtools
        config={{
          position: 'bottom-right',
        }}
        plugins={[
          {
            name: 'Tanstack Router',
            render: <TanStackRouterDevtoolsPanel />,
          },
          TanStackQueryDevtools,
        ]}
      />
    </>
  )
}
