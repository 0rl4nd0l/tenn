import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ThemeCandidate } from '@/types/cockpit-home';
import { Sparkles, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ThemeCandidatesCardProps {
  themes: ThemeCandidate[];
}

export function ThemeCandidatesCard({ themes }: ThemeCandidatesCardProps) {
  return (
    <Card className="terminal-panel h-full flex flex-col">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 border-b border-border/40 shrink-0">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5" />
          Evidence-Backed Themes
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0 flex-1">
        <div className="divide-y divide-border/30">
          {themes.map((theme) => (
            <div key={theme.label} className="p-4 hover:bg-accent/20 transition-colors group">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-sans font-bold text-foreground">
                    {theme.label}
                  </span>
                  <div className={cn(
                    "w-1.5 h-1.5 rounded-full",
                    theme.sentiment === 'positive' ? "bg-green-500" :
                    theme.sentiment === 'negative' ? "bg-red-500" :
                    "bg-muted-foreground"
                  )} />
                </div>
                <span className="text-[10px] font-mono text-cyan-500 px-1.5 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded">
                  {theme.evidenceCount} SOURCES
                </span>
              </div>
              <p className="text-[11px] font-sans text-muted-foreground leading-relaxed mb-3">
                {theme.description}
              </p>
              <button className="text-[10px] font-mono text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors uppercase tracking-tight">
                Inspect Evidence
                <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
              </button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
