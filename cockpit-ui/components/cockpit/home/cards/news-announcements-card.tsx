import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { NewsItem } from '@/types/cockpit-home';
import { EvidenceBadge } from '../evidence-badge';
import { MessageSquare, ExternalLink } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

interface NewsAnnouncementsCardProps {
  news: NewsItem[];
  onSelectItem?: (item: NewsItem) => void;
}

export function NewsAnnouncementsCard({ news, onSelectItem }: NewsAnnouncementsCardProps) {
  return (
    <Card className="terminal-panel h-full flex flex-col">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 shrink-0 border-b border-border/40">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground">
          Live News & Announcements
        </CardTitle>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            STREAMING
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 min-h-0">
        <ScrollArea className="h-[400px]">
          <div className="divide-y divide-border/40">
            {news.map((item) => (
              <div
                key={item.id}
                className="p-4 hover:bg-accent/30 cursor-pointer transition-colors group"
                onClick={() => onSelectItem?.(item)}
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono font-bold text-cyan-500 px-1.5 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded">
                      {item.ticker}
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {item.timestamp}
                    </span>
                  </div>
                  <EvidenceBadge level={item.trustLevel} />
                </div>
                <h4 className="text-[13px] font-sans font-medium leading-snug mb-3 group-hover:text-cyan-400 transition-colors">
                  {item.headline}
                </h4>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-muted-foreground/70 uppercase">
                    {item.source}
                  </span>
                  <div className="flex items-center gap-3">
                    <button className="text-[10px] font-mono text-muted-foreground hover:text-foreground flex items-center gap-1">
                      <MessageSquare className="w-3 h-3" />
                      ANALYZE
                    </button>
                    <button className="text-[10px] font-mono text-muted-foreground hover:text-foreground flex items-center gap-1">
                      <ExternalLink className="w-3 h-3" />
                      SOURCE
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
