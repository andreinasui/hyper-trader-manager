import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { traderKeys } from '@/lib/query-keys';
import { TraderCard } from '@/components/traders/TraderCard';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus, Bot, ArrowLeft } from 'lucide-react';

export const Route = createFileRoute('/_authenticated/traders/')({
  component: TradersPage,
});

function TradersPage() {
  const { data: traders, isLoading } = useQuery({
    queryKey: traderKeys.lists(),
    queryFn: () => api.listTraders(),
  });

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
            <div className="flex items-center gap-2">
              <Bot className="w-6 h-6" />
              <h1 className="text-2xl font-bold">Traders</h1>
            </div>
          </div>
          <Button asChild>
            <Link to="/traders/new">
              <Plus className="mr-2 h-4 w-4" />
              Create Trader
            </Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto p-6 md:p-8">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-24 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : traders && traders.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {traders.map((trader) => (
              <TraderCard key={trader.id} trader={trader} />
            ))}
          </div>
        ) : (
          <Card className="text-center py-12">
            <CardContent className="pt-6">
              <Bot className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <h2 className="text-xl font-semibold mb-2">No traders yet</h2>
              <p className="text-muted-foreground mb-4">
                Get started by creating your first trading bot
              </p>
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
