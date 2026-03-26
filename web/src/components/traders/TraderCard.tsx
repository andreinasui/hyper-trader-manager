import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from './StatusBadge';
import { Link } from '@tanstack/react-router';
import type { Trader } from '../../lib/types';

interface TraderCardProps {
  trader: Trader;
}

export function TraderCard({ trader }: TraderCardProps) {
  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader>
        <div className="flex justify-between items-start">
          <CardTitle className="text-xl">
            {trader.latest_config?.name || trader.runtime_name}
          </CardTitle>
          <StatusBadge status={trader.status} />
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
  );
}
