import { cn } from '@/lib/utils';
import { DataHealthItem } from '@/types/cockpit-home';

interface DataHealthStripProps {
  items: DataHealthItem[];
}

export function DataHealthStrip({ items }: DataHealthStripProps) {
  return (
    <div className="grid grid-cols-1 gap-2 border-b border-border bg-card/30 px-4 py-2 sm:grid-cols-2 xl:flex xl:flex-nowrap xl:items-center xl:gap-6 xl:py-1.5">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex min-w-0 items-center justify-between gap-2 rounded border border-border/40 bg-background/30 px-2 py-1 xl:justify-start xl:border-0 xl:bg-transparent xl:px-0 xl:py-0"
        >
          <span className="truncate text-[10px] font-mono uppercase text-muted-foreground">{item.label}:</span>
          <div className="flex min-w-0 items-center gap-1.5">
            <div
              className={cn(
                'h-1.5 w-1.5 shrink-0 rounded-full',
                item.status === 'healthy' && 'bg-green-500',
                item.status === 'degraded' && 'bg-amber-500',
                item.status === 'failed' && 'bg-red-500',
                item.status === 'stale' && 'bg-blue-500'
              )}
            />
            <span className="min-w-0 truncate text-[11px] font-mono font-medium text-foreground">
              {item.value || (item.status.toUpperCase())}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
