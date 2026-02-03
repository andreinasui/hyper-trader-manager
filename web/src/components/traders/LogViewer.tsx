import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';
import { useState } from 'react';

interface LogViewerProps {
  logs?: string[];
  onRefresh?: () => void;
}

export function LogViewer({ logs, onRefresh }: LogViewerProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    if (onRefresh) {
      await onRefresh();
    }
    setTimeout(() => setIsRefreshing(false), 500);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Logs</CardTitle>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="bg-muted rounded-md p-4 max-h-96 overflow-y-auto">
          <pre className="text-xs font-mono text-foreground whitespace-pre-wrap">
            {logs && logs.length > 0 ? logs.join('\n') : 'No logs available'}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
}
