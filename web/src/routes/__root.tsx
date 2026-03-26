import { Outlet, createRootRouteWithContext, useRouterState } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'

import Header from '../components/Header'
import TanStackQueryDevtools from '../integrations/tanstack-query/devtools'
import type { QueryClient } from '@tanstack/react-query'
import type { AuthState } from '@/hooks/useAuth'
import type { LoginRequest } from '@/lib/types'

interface MyRouterContext {
  queryClient: QueryClient
  auth: AuthState & {
      login: (data: LoginRequest) => Promise<void>
      logout: () => Promise<void>
      checkAuth: () => Promise<void>
      ready: boolean
  }
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  component: RootComponent,
})

function RootComponent() {
  const router = useRouterState()
  const currentPath = router.location.pathname
  
  // Don't show Header on login (root path), dashboard, or trader routes
  // Wait, dashboard should probably show header?
  // Let's keep it as is for now to avoid breaking layout changes unrelated to auth.
  const hideHeader = currentPath === '/' || 
                     currentPath === '/register'
  
  return (
    <>
      {!hideHeader && <Header />}
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
