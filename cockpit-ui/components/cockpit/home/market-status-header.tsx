import { cn } from '@/lib/utils';
import { MarketSessionState } from '@/types/cockpit-home';
import { Clock, Zap, AlertTriangle } from 'lucide-react';

interface MarketStatusHeaderProps {
  session: MarketSessionState;
  melbourneTime: string;
  nextEvent: string;
  systemStatus?: 'operational' | 'partial' | 'degraded' | 'data_missing';
}

export function MarketStatusHeader({
  session,
  melbourneTime,
  nextEvent,
  systemStatus = 'operational',
}: MarketStatusHeaderProps) {
  const getSessionConfig = (s: MarketSessionState) => {
    switch (s) {
      case 'OPEN':
        return { label: 'MARKET OPEN', color: 'text-green-500', icon: Zap, bg: 'bg-green-500/10' };
      case 'PRE_MARKET':
        return { label: 'PRE-MARKET', color: 'text-amber-500', icon: Clock, bg: 'bg-amber-500/10' };
      case 'POST_MARKET':
        return { label: 'POST-MARKET', color: 'text-blue-500', icon: Clock, bg: 'bg-blue-500/10' };
      case 'DEGRADED':
        return { label: 'DEGRADED STATE', color: 'text-red-500', icon: AlertTriangle, bg: 'bg-red-500/10' };
      default:
        return { label: 'CLOSED', color: 'text-muted-foreground', icon: Clock, bg: 'bg-muted/10' };
    }
  };

  const config = getSessionConfig(session);
  const Icon = config.icon;
  const statusConfig = {
    operational: { label: 'OPERATIONAL', color: 'text-green-500', dot: 'bg-green-500' },
    partial: { label: 'PARTIAL', color: 'text-amber-500', dot: 'bg-amber-500' },
    degraded: { label: 'DEGRADED', color: 'text-red-500', dot: 'bg-red-500' },
    data_missing: { label: 'DATA_MISSING', color: 'text-red-500', dot: 'bg-red-500' },
  }[systemStatus];

  return (
    <header className="sticky top-0 z-30 flex flex-col gap-3 border-b border-border bg-background/50 px-4 py-3 backdrop-blur-sm md:flex-row md:items-center md:justify-between md:px-6 md:py-4">
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center md:gap-6">
        <div className="flex flex-col">
          <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Workspace</span>
          <span className="text-[15px] font-sans font-bold text-foreground">Cockpit Overview</span>
        </div>
        
        <div className="mx-2 hidden h-8 w-[1px] bg-border/50 md:block" />

        <div className="flex min-w-0 flex-wrap items-center gap-3 md:gap-4">
          <div className={cn("flex items-center gap-2 px-3 py-1 rounded border", config.bg, config.color, "border-current/20")}>
            <Icon className="h-3.5 w-3.5 shrink-0" />
            <span className="text-[11px] font-mono font-bold tracking-wider">{config.label}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-mono text-muted-foreground uppercase">Melbourne Time</span>
            <span className="text-[13px] font-mono font-medium text-foreground">{melbourneTime}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-mono text-muted-foreground uppercase">Next Event</span>
            <span className="text-[13px] font-mono font-medium text-foreground">{nextEvent}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex flex-col items-start md:items-end">
          <span className="text-[10px] font-mono text-muted-foreground uppercase">System Status</span>
          <span className={cn("text-[11px] font-mono font-bold flex items-center gap-1.5", statusConfig.color)}>
            <span className={cn("w-1.5 h-1.5 rounded-full", statusConfig.dot)} />
            {statusConfig.label}
          </span>
        </div>
      </div>
    </header>
  );
}
