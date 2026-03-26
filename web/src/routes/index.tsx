import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { LoginForm } from '@/components/auth/LoginForm';

export const Route = createFileRoute('/')({
  component: LoginPage,
});

function LoginPage() {
  const { authenticated, loading, isInitialized, checkSetup } = useAuth();
  const navigate = useNavigate();

  // Re-check setup status on mount to ensure we have the latest
  useEffect(() => {
    checkSetup();
  }, [checkSetup]);

  useEffect(() => {
    if (loading) return;

    if (!isInitialized) {
      navigate({ to: '/setup' });
      return;
    }

    if (authenticated) {
      const returnUrl = sessionStorage.getItem('auth_return_url');
      if (returnUrl) {
        sessionStorage.removeItem('auth_return_url');
        window.location.href = returnUrl;
      } else {
        navigate({ to: '/dashboard' });
      }
    }
  }, [authenticated, loading, isInitialized, navigate]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight">HyperTrader</h1>
          <p className="mt-2 text-muted-foreground">
            Professional copy trading manager
          </p>
        </div>
        <LoginForm />
      </div>
    </div>
  );
}
