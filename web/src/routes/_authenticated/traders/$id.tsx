import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '../../../components/traders/StatusBadge';
import { LogViewer } from '../../../components/traders/LogViewer';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Play, Square, Trash2, Settings } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { useNavigate } from '@tanstack/react-router';

export const Route = createFileRoute('/_authenticated/traders/$id')({
  component: TraderDetailPage,
});

function TraderDetailPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: trader, isLoading } = useQuery({
    queryKey: ['trader', id],
    queryFn: () => api.getTrader(id),
  });

  const { data: logs } = useQuery({
    queryKey: ['trader-logs', id],
    queryFn: () => api.getTraderLogs(id),
  });

  const startMutation = useMutation({
    mutationFn: () => api.startTrader(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trader', id] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => api.stopTrader(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trader', id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteTrader(id),
    onSuccess: () => {
      navigate({ to: '/dashboard' });
    },
  });

  const refreshLogs = async () => {
    await queryClient.invalidateQueries({ queryKey: ['trader-logs', id] });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <header className="border-b border-border bg-card">
          <div className="container mx-auto p-4">
            <Skeleton className="h-8 w-64" />
          </div>
        </header>
        <main className="container mx-auto p-6 md:p-8">
          <Skeleton className="h-64 w-full" />
        </main>
      </div>
    );
  }

  if (!trader) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card>
          <CardContent className="pt-6">
            <p>Trader not found</p>
            <Button asChild className="mt-4">
              <Link to="/dashboard">Back to Dashboard</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex justify-between items-center p-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" asChild>
              <Link to="/dashboard">
                <ArrowLeft className="h-5 w-5" />
              </Link>
            </Button>
            <div>
              <h1 className="text-2xl font-bold">
                {trader.latest_config?.name || trader.k8s_name}
              </h1>
              <p className="text-sm text-muted-foreground">
                {trader.latest_config?.exchange || 'hyperliquid'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={trader.status} />
          </div>
        </div>
      </header>

      <main className="container mx-auto p-6 md:p-8 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Controls</CardTitle>
            <CardDescription>Manage your trading bot</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            {trader.status === 'running' ? (
              <Button
                variant="outline"
                onClick={() => stopMutation.mutate()}
                disabled={stopMutation.isPending}
              >
                <Square className="mr-2 h-4 w-4" />
                Stop
              </Button>
            ) : (
              <Button
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
              >
                <Play className="mr-2 h-4 w-4" />
                Start
              </Button>
            )}
            <Button variant="outline" asChild>
              <a href={`/traders/${id}/settings`}>
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </a>
            </Button>
            <Separator orientation="vertical" className="h-9" />
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive">
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. This will permanently delete the trader
                    and remove all associated data.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => deleteMutation.mutate()}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Status</p>
                <p className="text-base">{trader.status}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Exchange</p>
                <p className="text-base">{trader.latest_config?.exchange || 'hyperliquid'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Wallet Address</p>
                <p className="text-base font-mono text-xs">{trader.wallet_address}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">K8s Name</p>
                <p className="text-base">{trader.k8s_name}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <LogViewer logs={logs} onRefresh={refreshLogs} />
      </main>
    </div>
  );
}
