import { cn } from '@/lib/utils';
import { MarketSessionState } from '@/types/cockpit-home';
import { Clock, Zap, AlertTriangle } from 'lucide-react';

interface MarketStatusHeaderProps {
  session: MarketSessionState;
  melbourneTime: string;
  nextEvent: string;
}

export function MarketStatusHeader({ session, melbourneTime, nextEvent }: MarketStatusHeaderProps) {
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

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-background/50 backdrop-blur-sm border-b border-border sticky top-0 z-30">
      <div className="flex items-center gap-6">
        <div className="flex flex-col">
          <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Workspace</span>
          <span className="text-[15px] font-sans font-bold text-foreground">Cockpit Overview</span>
        </div>
        
        <div className="h-8 w-[1px] bg-border/50 mx-2" />

        <div className="flex items-center gap-4">
          <div className={cn("flex items-center gap-2 px-3 py-1 rounded border", config.bg, config.color, "border-current/20")}>
            <Icon className="w-3.5 h-3.5" />
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
        <div className="flex flex-col items-end">
          <span className="text-[10px] font-mono text-muted-foreground uppercase">System Status</span>
          <span className="text-[11px] font-mono text-green-500 font-bold flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            OPERATIONAL
          </span>
        </div>
      </div>
    </header>
  );
}
