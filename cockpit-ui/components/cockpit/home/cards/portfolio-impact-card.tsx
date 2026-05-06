import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CockpitHomeState } from '@/types/cockpit-home';
import { cn } from '@/lib/utils';
import { Wallet, ShieldCheck } from 'lucide-react';

interface PortfolioImpactCardProps {
  portfolio: CockpitHomeState['portfolio'];
}

export function PortfolioImpactCard({ portfolio }: PortfolioImpactCardProps) {
  const isPositive = portfolio.dayChange >= 0;

  return (
    <Card className="terminal-panel h-full border-l-2 border-l-cyan-500/50">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Wallet className="w-3.5 h-3.5" />
          My Portfolio Impact
        </CardTitle>
        <div className="flex items-center gap-1.5 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
          <ShieldCheck className="w-3 h-3 text-cyan-400" />
          <span className="text-[10px] font-mono text-cyan-400 font-bold">{portfolio.coverage}% COV</span>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground/60">Total Value (Local)</span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold tracking-tight text-foreground">
              ${portfolio.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-mono uppercase text-muted-foreground/60">Day Change</span>
            <span className={cn(
              "text-[15px] font-mono font-bold",
              isPositive ? "text-green-500" : "text-red-500"
            )}>
              {isPositive ? '+' : ''}${portfolio.dayChange.toLocaleString()}
            </span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-mono uppercase text-muted-foreground/60">Change %</span>
            <span className={cn(
              "text-[15px] font-mono font-bold",
              isPositive ? "text-green-500" : "text-red-500"
            )}>
              {isPositive ? '+' : ''}{portfolio.dayChangePercent}%
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
