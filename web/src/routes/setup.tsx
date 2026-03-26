import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { BootstrapForm } from '@/components/auth/BootstrapForm'

export const Route = createFileRoute('/setup')({
  component: SetupPage,
})

function SetupPage() {
  const { isInitialized, loading, checkSetup } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    // Re-check setup status on mount
    checkSetup()
  }, [checkSetup])

  useEffect(() => {
    if (!loading && isInitialized) {
      navigate({ to: '/' })
    }
  }, [loading, isInitialized, navigate])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight">Welcome to HyperTrader</h1>
          <p className="mt-2 text-muted-foreground">
            Complete the initial setup to secure your trading manager.
          </p>
        </div>
        <BootstrapForm />
      </div>
    </div>
  )
}
