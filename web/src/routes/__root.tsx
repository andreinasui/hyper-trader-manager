import { Outlet, createRootRouteWithContext, useRouterState } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'

import Header from '../components/Header'

import TanStackQueryDevtools from '../integrations/tanstack-query/devtools'

import type { QueryClient } from '@tanstack/react-query'

interface MyRouterContext {
  queryClient: QueryClient
  auth: {
    ready: boolean
    authenticated: boolean
    user: { walletAddress: string; privyUserId: string } | null
    loading: boolean
  }
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  component: RootComponent,
})

function RootComponent() {
  const router = useRouterState()
  const currentPath = router.location.pathname
  
  // Don't show Header on login (root path), dashboard, or trader routes
  const hideHeader = currentPath === '/' || 
                     currentPath === '/register' ||
                     currentPath === '/dashboard' ||
                     currentPath.startsWith('/traders') ||
                     currentPath.startsWith('/settings') ||
                     currentPath.startsWith('/admin')
  
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
