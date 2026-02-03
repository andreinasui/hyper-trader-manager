import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Wallet, Shield, Key, RefreshCw, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export const Route = createFileRoute('/')({
  component: LoginPage,
});

function LoginPage() {
  const { authenticated, loading, login } = useAuth();
  const navigate = useNavigate();
  const [loginError, setLoginError] = useState<string | null>(null);

  useEffect(() => {
    if (authenticated && !loading) {
      // Check for return URL in sessionStorage
      const returnUrl = sessionStorage.getItem('auth_return_url');
      
      if (returnUrl) {
        // Clear the stored URL
        sessionStorage.removeItem('auth_return_url');
        // Navigate to the stored URL
        window.location.href = returnUrl;
      } else {
        // Default redirect to dashboard
        navigate({ to: '/dashboard' });
      }
    }
  }, [authenticated, loading, navigate]);

  const handleLogin = async () => {
    try {
      setLoginError(null);
      await login();
    } catch (error) {
      console.error('Login error:', error);
      setLoginError('Failed to connect wallet. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Connecting to wallet...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="rounded-full bg-primary/10 p-3">
              <Wallet className="h-8 w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">
            Welcome to HyperTrader
          </CardTitle>
          <CardDescription>
            Connect your wallet to start copy trading on Hyperliquid
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {loginError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{loginError}</AlertDescription>
            </Alert>
          )}
          
          <Button
            onClick={handleLogin}
            className="w-full"
            size="lg"
          >
            <Wallet className="mr-2 h-5 w-5" />
            Connect Wallet
          </Button>
          
          <div className="space-y-3 pt-2">
            <div className="flex items-start space-x-3 text-sm">
              <Shield className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Secure Authentication</p>
                <p className="text-muted-foreground">
                  Supports MetaMask, Rabby, and other wallets
                </p>
              </div>
            </div>
            
            <div className="flex items-start space-x-3 text-sm">
              <Key className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Your Keys, Your Control</p>
                <p className="text-muted-foreground">
                  Your private keys never leave your wallet
                </p>
              </div>
            </div>
            
            <div className="flex items-start space-x-3 text-sm">
              <RefreshCw className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Automated Agent Wallets</p>
                <p className="text-muted-foreground">
                  Secure agent wallets for automated trading with daily rotation
                </p>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t">
            <p className="text-xs text-center text-muted-foreground">
              By connecting your wallet, you agree to our Terms of Service and Privacy Policy
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
