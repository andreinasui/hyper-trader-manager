import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { useAuth } from '@/hooks/useAuth'

export const Route = createFileRoute('/_authenticated')({
  component: AuthenticatedLayout,
  beforeLoad: ({ context, location }) => {
    const { auth } = context
    
    // If auth is ready and user is not authenticated, save return URL and redirect to login
    if (auth.ready && !auth.authenticated) {
      // Save current location to sessionStorage for return after login
      sessionStorage.setItem('auth_return_url', location.href)
      throw redirect({ to: '/' })
    }
    
    // If auth is not ready, let the component handle the loading state
  },
})

function AuthenticatedLayout() {
  const { ready, authenticated, loading } = useAuth()

  // Show loading state while Privy initializes
  if (!ready || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  // This should never render if not authenticated (beforeLoad handles redirect)
  // but keeping as safety check
  if (!authenticated) {
    return null
  }

  // Render protected content
  return <Outlet />
}
