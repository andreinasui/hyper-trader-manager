import { Outlet, createRootRouteWithContext, useNavigate, useRouterState } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'
import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'

import TanStackQueryDevtools from '../integrations/tanstack-query/devtools'
import { getSSLStatus } from '@/api/ssl-setup'

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
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  const { data: sslStatus, isError: isSslError } = useQuery({
    queryKey: ['ssl-status'],
    queryFn: getSSLStatus,
    staleTime: Infinity, // Only check once per session
    retry: false,
    refetchOnWindowFocus: false,
  })

  useEffect(() => {
    // If the SSL status check fails, let the app proceed — don't block startup
    if (isSslError) return
    if (sslStatus && !sslStatus.ssl_configured && !pathname.startsWith('/setup/ssl')) {
      void navigate({ to: '/setup/ssl' })
    }
  }, [sslStatus, isSslError, pathname, navigate])

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
