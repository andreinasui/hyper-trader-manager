import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus, LogOut, Settings, Bot, CheckCircle, Square, AlertCircle } from 'lucide-react';

export const Route = createFileRoute('/_authenticated/dashboard')({
  component: DashboardPage,
});

function DashboardPage() {
  const { user, logout } = useAuth();
  const { data: traders, isLoading } = useQuery({
    queryKey: ['traders'],
    queryFn: () => api.listTraders(),
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return (
          <Badge className="bg-emerald-900/50 text-emerald-300 border-emerald-500/50">
            <CheckCircle className="w-3 h-3 mr-1" />
            Running
          </Badge>
        );
      case 'stopped':
        return (
          <Badge variant="secondary">
            <Square className="w-3 h-3 mr-1" />
            Stopped
          </Badge>
        );
      case 'error':
        return (
          <Badge variant="destructive">
            <AlertCircle className="w-3 h-3 mr-1" />
            Error
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex justify-between items-center p-4">
          <div className="flex items-center gap-2">
            <Bot className="w-6 h-6" />
            <h1 className="text-2xl font-bold">HyperTrader</h1>
          </div>
          <div className="flex items-center gap-4">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-9 px-3" data-testid="user-menu-trigger">
                  <Avatar className="h-7 w-7 mr-2">
                    <AvatarFallback>
                      {user?.username?.slice(0, 2).toUpperCase() || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm">
                    {user?.username || 'User'}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user?.username}</p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.is_admin ? 'Administrator' : 'User'}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/settings" className="cursor-pointer">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={logout}
                  className="cursor-pointer text-destructive focus:text-destructive"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <main className="container mx-auto p-6 md:p-8">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">Manage your trading bots</p>
          </div>
          <Button asChild>
            <Link to="/traders/new">
              <Plus className="mr-2 h-4 w-4" />
              Create Trader
            </Link>
          </Button>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-20 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : traders && traders.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {traders.map((trader) => (
              <Card key={trader.id} className="hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-xl">
                      {trader.latest_config?.name || trader.runtime_name}
                    </CardTitle>
                    {getStatusBadge(trader.status)}
                  </div>
                  <CardDescription>
                    {trader.latest_config?.exchange || 'hyperliquid'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button variant="outline" asChild className="w-full">
                    <Link to="/traders/$id" params={{ id: trader.id }}>
                      View Details
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="text-center py-12">
            <CardContent className="pt-6">
              <Bot className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <CardTitle className="mb-2">No traders yet</CardTitle>
              <CardDescription className="mb-4">
                Get started by creating your first trading bot
              </CardDescription>
              <Button asChild>
                <Link to="/traders/new">
                  <Plus className="mr-2 h-4 w-4" />
                  Create your first trader
                </Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
