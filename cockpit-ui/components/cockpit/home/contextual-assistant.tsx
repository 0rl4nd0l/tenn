'use client'

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { NewsItem } from '@/types/cockpit-home';
import { EvidenceBadge } from './evidence-badge';
import { Bot, Sparkles, Send, Paperclip, ChevronRight, Maximize2 } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ContextualAssistantProps {
  attachedItem: NewsItem | null;
  onClearContext: () => void;
}

export function ContextualAssistant({ attachedItem, onClearContext }: ContextualAssistantProps) {
  const suggestedPrompts = attachedItem
    ? [
        `Is this acquisition material for ${attachedItem.ticker}?`,
        `Compare to prior ${attachedItem.ticker} deals.`,
        "What are the market implications?",
        "Update my thesis note."
      ]
    : [
        "Summarize today's session.",
        "Show my top portfolio risks.",
        "Check morning announcements.",
        "Prepare tomorrow's watchlist."
      ];

  return (
    <Card className="terminal-panel h-full flex flex-col bg-card/20 border-l border-border/50">
      <CardHeader className="py-4 px-5 border-b border-border/40 flex flex-row items-center justify-between shrink-0">
        <div className="flex flex-col">
          <CardTitle className="text-[12px] font-mono uppercase tracking-widest text-cyan-500 flex items-center gap-2">
            <Bot className="w-4 h-4" />
            Tenn Assistant
          </CardTitle>
          <Link href="/full-chat" className="text-[9px] font-mono text-muted-foreground hover:text-cyan-500 flex items-center gap-1 mt-1 transition-colors">
            <Maximize2 className="w-2.5 h-2.5" />
            OPEN FULL CHAT
          </Link>
        </div>
        <span className="text-[10px] font-mono text-muted-foreground/60 italic tracking-tight">
          CONTEXT_AWARE_v2
        </span>
      </CardHeader>
      
      <CardContent className="p-0 flex-1 flex flex-col min-h-0">
        <ScrollArea className="flex-1">
          <div className="p-5 space-y-6">
            {attachedItem && (
              <div className="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-3 space-y-2 relative group">
                <button
                  onClick={onClearContext}
                  className="absolute -top-2 -right-2 bg-background border border-border rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <span className="sr-only">Clear Context</span>
                  <svg className="w-3 h-3 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase">Attached Evidence</span>
                  <EvidenceBadge level={attachedItem.trustLevel} className="scale-90" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono font-bold text-foreground">{attachedItem.ticker}</span>
                  <span className="text-[11px] font-sans text-muted-foreground truncate">{attachedItem.headline}</span>
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <div className="w-6 h-6 rounded bg-cyan-600/20 flex items-center justify-center shrink-0 border border-cyan-500/30">
                <Bot className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <div className="space-y-4 flex-1">
                <p className="text-[13px] font-sans text-muted-foreground leading-relaxed">
                  {attachedItem
                    ? `I have attached the **${attachedItem.ticker}** announcement. How would you like me to analyze this source?`
                    : "I am monitoring the market session. You can ask me to summarize current movers, check your portfolio impact, or analyze specific news items."}
                </p>

                <div className="space-y-2">
                  <span className="text-[10px] font-mono uppercase text-muted-foreground/60 tracking-wider">Suggested Queries</span>
                  <div className="flex flex-col gap-1.5">
                    {suggestedPrompts.map((prompt) => (
                      <button
                        key={prompt}
                        className="text-left text-[11px] font-sans text-foreground bg-accent/30 hover:bg-accent/50 px-3 py-2 rounded border border-border/40 transition-colors flex items-center justify-between group"
                      >
                        {prompt}
                        <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-cyan-500" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ScrollArea>

        <div className="p-4 border-t border-border/40 bg-background/30 space-y-3 shrink-0">
          <div className="relative">
            <textarea
              placeholder="Ask Tenn about the market..."
              className="w-full bg-card/50 border border-border/60 rounded-lg p-3 pr-10 text-[13px] font-sans min-h-[80px] focus:outline-none focus:border-cyan-500/50 resize-none placeholder:text-muted-foreground/50"
            />
            <div className="absolute bottom-3 right-3 flex items-center gap-2">
              <Paperclip className="w-4 h-4 text-muted-foreground cursor-pointer hover:text-foreground" />
              <div className="w-7 h-7 bg-cyan-600 rounded flex items-center justify-center cursor-pointer hover:bg-cyan-500 transition-colors">
                <Send className="w-3.5 h-3.5 text-white" />
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between px-1">
            <span className="text-[10px] font-mono text-muted-foreground flex items-center gap-1.5 uppercase">
              <Sparkles className="w-3 h-3 text-cyan-500" />
              Evidence-Bound Synthesis
            </span>
            <span className="text-[10px] font-mono text-muted-foreground/40 italic uppercase">
              Shift + Enter for new line
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
