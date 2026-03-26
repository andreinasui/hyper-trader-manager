import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { api } from '@/lib/api';
import type { CreateTraderRequest } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { ArrowLeft, Bot, ShieldAlert } from 'lucide-react';
import { useState } from 'react';

export const Route = createFileRoute('/_authenticated/traders/new')({
  component: CreateTraderPage,
});

interface TraderFormData {
  name: string;
  walletAddress: string;
  privateKey: string;
  copyAddress: string;
  network: 'mainnet' | 'testnet';
}

function CreateTraderPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TraderFormData>({
    defaultValues: {
      network: 'mainnet',
    },
  });

  const createMutation = useMutation({
    mutationFn: async (data: TraderFormData) => {
      const request: CreateTraderRequest = {
        wallet_address: data.walletAddress,
        private_key: data.privateKey,
        config: {
          name: data.name,
          exchange: 'hyperliquid',
          self_account: {
            address: data.walletAddress,
            base_url: data.network,
          },
          copy_account: {
            address: data.copyAddress,
            base_url: data.network,
          },
        },
      };

      return api.createTrader(request);
    },
    onSuccess: () => {
      navigate({ to: '/dashboard' });
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const onSubmit = (data: TraderFormData) => {
    setError(null);
    createMutation.mutate(data);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex items-center gap-4 p-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/dashboard">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div className="flex items-center gap-2">
            <Bot className="w-6 h-6" />
            <h1 className="text-2xl font-bold">Create New Trader</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto p-6 md:p-8 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Trading Bot Configuration</CardTitle>
            <CardDescription>
              Set up a new trading bot to copy trades from another wallet
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {error && (
                <Alert role="alert" className="border-destructive bg-destructive/10 text-destructive">
                  {error}
                </Alert>
              )}

              {/* Security Info */}
              <div className="bg-amber-950/30 border border-amber-500/50 rounded-lg p-4">
                <div className="flex gap-3">
                  <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div className="space-y-2 text-sm">
                    <p className="font-semibold text-amber-300">Private Key Security</p>
                    <p className="text-amber-100">
                      Your private key is encrypted before storage and is only decrypted when
                      the trading bot needs to sign transactions. Never share your private key
                      with anyone.
                    </p>
                  </div>
                </div>
              </div>

              {/* Trader Name */}
              <div className="space-y-2">
                <Label htmlFor="name">Trader Name *</Label>
                <Input
                  id="name"
                  {...register('name', { 
                    required: 'Trader name is required',
                    minLength: { value: 3, message: 'Name must be at least 3 characters' }
                  })}
                  placeholder="My Copy Trader"
                />
                {errors.name && (
                  <p className="text-sm text-destructive" role="alert">{errors.name.message}</p>
                )}
              </div>

              {/* Wallet Address */}
              <div className="space-y-2">
                <Label htmlFor="walletAddress">Trading Wallet Address *</Label>
                <Input
                  id="walletAddress"
                  {...register('walletAddress', { 
                    required: 'Wallet address is required',
                    pattern: {
                      value: /^0x[a-fA-F0-9]{40}$/,
                      message: 'Invalid Ethereum address'
                    }
                  })}
                  placeholder="0x..."
                />
                {errors.walletAddress && (
                  <p className="text-sm text-destructive" role="alert">{errors.walletAddress.message}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  The wallet address that will execute trades
                </p>
              </div>

              {/* Private Key */}
              <div className="space-y-2">
                <Label htmlFor="privateKey">Private Key *</Label>
                <Input
                  id="privateKey"
                  type="password"
                  {...register('privateKey', { 
                    required: 'Private key is required',
                    pattern: {
                      value: /^(0x)?[a-fA-F0-9]{64}$/,
                      message: 'Invalid private key format'
                    }
                  })}
                  placeholder="0x..."
                />
                {errors.privateKey && (
                  <p className="text-sm text-destructive" role="alert">{errors.privateKey.message}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  The private key for signing transactions (will be encrypted)
                </p>
              </div>

              {/* Exchange (read-only) */}
              <div className="space-y-2">
                <Label>Exchange</Label>
                <div className="px-3 py-2 bg-muted rounded-md text-muted-foreground">
                  Hyperliquid
                </div>
                <p className="text-xs text-muted-foreground">
                  Currently, only Hyperliquid exchange is supported
                </p>
              </div>

              {/* Copy Address */}
              <div className="space-y-2">
                <Label htmlFor="copyAddress">Copy Trader Address *</Label>
                <Input
                  id="copyAddress"
                  {...register('copyAddress', { 
                    required: 'Copy address is required',
                    pattern: {
                      value: /^0x[a-fA-F0-9]{40}$/,
                      message: 'Invalid Ethereum address'
                    }
                  })}
                  placeholder="0x..."
                />
                {errors.copyAddress && (
                  <p className="text-sm text-destructive" role="alert">{errors.copyAddress.message}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  The wallet address to copy trades from
                </p>
              </div>

              {/* Network */}
              <div className="space-y-2">
                <Label htmlFor="network">Network *</Label>
                <select
                  id="network"
                  {...register('network')}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <option value="mainnet">Mainnet</option>
                  <option value="testnet">Testnet</option>
                </select>
                <p className="text-xs text-muted-foreground">
                  Testnet recommended for testing your strategy first
                </p>
              </div>

              {/* Submit */}
              <div className="flex gap-3 pt-4">
                <Button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex-1"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Trader'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  asChild
                >
                  <Link to="/dashboard">Cancel</Link>
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
