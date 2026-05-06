import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BookOpen, Calendar } from 'lucide-react';

interface SessionSummaryCardProps {
  summary: string;
  tomorrowPrep?: string[];
}

export function SessionSummaryCard({ summary, tomorrowPrep }: SessionSummaryCardProps) {
  return (
    <Card className="terminal-panel h-full flex flex-col">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 border-b border-border/40 shrink-0">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <BookOpen className="w-3.5 h-3.5" />
          Session Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 flex-1 space-y-6">
        <div>
          <p className="text-[14px] font-sans text-foreground leading-relaxed">
            {summary}
          </p>
        </div>

        {tomorrowPrep && tomorrowPrep.length > 0 && (
          <div className="space-y-3">
            <h5 className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Calendar className="w-3 h-3" />
              Tomorrow Prep
            </h5>
            <div className="space-y-2">
              {tomorrowPrep.map((item, idx) => (
                <div key={idx} className="flex gap-3 text-[12px] font-sans text-muted-foreground leading-tight p-2 bg-accent/20 rounded border border-border/30">
                  <span className="text-cyan-500 font-mono">0{idx + 1}</span>
                  {item}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
