import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MarketMover, CockpitHomeState } from '@/types/cockpit-home';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MarketPulseCardProps {
  movers: MarketMover[];
  overnightLead?: CockpitHomeState['overnightLead'];
}

export function MarketPulseCard({ movers, overnightLead }: MarketPulseCardProps) {
  return (
    <Card className="terminal-panel h-full">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground">
          {overnightLead ? 'Overnight Lead' : 'Market Pulse'}
        </CardTitle>
        <span className="text-[10px] font-mono text-cyan-500/70">
          {overnightLead ? 'GLOBAL_DESK' : 'LIVE_FEED'}
        </span>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-3">
        {overnightLead && (
          <div className="bg-cyan-500/5 border border-cyan-500/20 rounded p-3 mb-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-mono font-bold text-foreground">{overnightLead.market}</span>
              <span className="text-[11px] font-mono text-green-500">+{overnightLead.changePercent}%</span>
            </div>
            <p className="text-[11px] font-sans text-muted-foreground leading-tight">
              {overnightLead.summary}
            </p>
          </div>
        )}
        {movers.map((mover) => (
          <div key={mover.ticker} className="flex items-center justify-between group">
            <div className="flex flex-col">
              <span className="text-[13px] font-mono font-bold text-foreground group-hover:text-cyan-400 transition-colors">
                {mover.ticker}
              </span>
              <span className="text-[10px] font-mono text-muted-foreground truncate max-w-[120px]">
                {mover.reason}
              </span>
            </div>
            <div className="flex flex-col items-end">
              <div className="flex items-center gap-1">
                {mover.change >= 0 ? (
                  <TrendingUp className="w-3 h-3 text-green-500" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-red-500" />
                )}
                <span className={cn(
                  "text-[13px] font-mono font-medium",
                  mover.change >= 0 ? "text-green-500" : "text-red-500"
                )}>
                  {mover.change >= 0 ? '+' : ''}{mover.changePercent.toFixed(2)}%
                </span>
              </div>
              <span className="text-[11px] font-mono text-muted-foreground/70">
                {mover.price.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
