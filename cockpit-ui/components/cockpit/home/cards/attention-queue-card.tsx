import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CockpitHomeState } from '@/types/cockpit-home';
import { ListChecks, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AttentionQueueCardProps {
  items: CockpitHomeState['attentionQueue'];
}

export function AttentionQueueCard({ items }: AttentionQueueCardProps) {
  return (
    <Card className="terminal-panel h-full">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 border-b border-border/40">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <ListChecks className="w-3.5 h-3.5" />
          Attention Queue
        </CardTitle>
        <span className="text-[10px] font-mono text-muted-foreground bg-accent/50 px-1.5 py-0.5 rounded">
          {items.length} ITEMS
        </span>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border/30">
          {items.map((item) => (
            <div key={item.id} className="p-4 hover:bg-accent/20 transition-colors">
              <div className="flex items-start gap-3">
                <div className={cn(
                  "mt-0.5 p-1 rounded-sm border",
                  item.priority === 'high' ? "bg-red-500/10 border-red-500/20 text-red-500" :
                  item.priority === 'medium' ? "bg-amber-500/10 border-amber-500/20 text-amber-500" :
                  "bg-blue-500/10 border-blue-500/20 text-blue-500"
                )}>
                  <AlertCircle className="w-3.5 h-3.5" />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-[13px] font-sans font-semibold text-foreground leading-tight">
                    {item.label}
                  </span>
                  <p className="text-[11px] font-sans text-muted-foreground leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
