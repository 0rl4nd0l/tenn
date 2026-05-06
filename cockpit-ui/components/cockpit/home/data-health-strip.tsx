import { cn } from '@/lib/utils';
import { DataHealthItem } from '@/types/cockpit-home';

interface DataHealthStripProps {
  items: DataHealthItem[];
}

export function DataHealthStrip({ items }: DataHealthStripProps) {
  return (
    <div className="flex items-center gap-6 px-4 py-1.5 border-b border-border bg-card/30 overflow-x-auto no-scrollbar">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-2 whitespace-nowrap">
          <span className="text-[10px] font-mono uppercase text-muted-foreground">{item.label}:</span>
          <div className="flex items-center gap-1.5">
            <div
              className={cn(
                'w-1.5 h-1.5 rounded-full',
                item.status === 'healthy' && 'bg-green-500',
                item.status === 'degraded' && 'bg-amber-500',
                item.status === 'failed' && 'bg-red-500',
                item.status === 'stale' && 'bg-blue-500'
              )}
            />
            <span className="text-[11px] font-mono font-medium text-foreground">
              {item.value || (item.status.toUpperCase())}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
