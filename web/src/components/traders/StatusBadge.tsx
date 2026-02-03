import { Badge } from '@/components/ui/badge';
import { CheckCircle, Square, AlertCircle } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  switch (status.toLowerCase()) {
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
}
