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
  const suggestedPrompts = (attachedItem
    ? [
        { label: `Assess this source for ${attachedItem.ticker || 'the selected ticker'}.`, enabled: true },
        { label: `Compare with prior ${attachedItem.ticker || 'ticker'} context.`, enabled: true },
        { label: "What evidence is available?", enabled: true },
        { label: "Update my thesis note.", enabled: false }
      ]
    : [
        { label: "Summarize today's session.", enabled: true },
        { label: "Show my top portfolio risks.", enabled: true },
        { label: "Check morning announcements.", enabled: true },
        { label: "Prepare tomorrow's watchlist.", enabled: true }
      ]);
  const defaultPrompt = attachedItem
    ? `Assess this source for ${attachedItem.ticker || 'the selected ticker'}.`
    : "Summarize today's session.";
  const defaultChatHref = buildChatHandoffHref(defaultPrompt, attachedItem);

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
                  <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase">Attached Home Source</span>
                  <EvidenceBadge level={attachedItem.trustLevel} className="scale-90" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono font-bold text-foreground">{attachedItem.ticker}</span>
                  <span className="text-[11px] font-sans text-muted-foreground truncate">{attachedItem.headline}</span>
                </div>
                <div className="text-[10px] font-mono text-muted-foreground break-all">
                  {attachedItem.sourceId ? `source_id=${attachedItem.sourceId}` : 'source_id=DATA_MISSING'}
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
                    ? `I have attached the ${attachedItem.ticker || 'selected'} Home source context. How would you like me to analyze this source?`
                    : "I am monitoring the market session. You can ask me to summarize current movers, check your portfolio impact, or analyze specific news items."}
                </p>

                <div className="space-y-2">
                  <span className="text-[10px] font-mono uppercase text-muted-foreground/60 tracking-wider">Suggested Queries</span>
                  <div className="flex flex-col gap-1.5">
                    {suggestedPrompts.map((prompt) => (
                      prompt.enabled ? (
                        <Link
                          key={prompt.label}
                          href={buildChatHandoffHref(prompt.label, attachedItem)}
                          className="text-left text-[11px] font-sans text-foreground bg-accent/30 hover:bg-accent/50 px-3 py-2 rounded border border-border/40 transition-colors flex items-center justify-between group"
                          aria-label={`Open full chat with prompt: ${prompt.label}`}
                        >
                          {prompt.label}
                          <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-cyan-500" />
                        </Link>
                      ) : (
                        <div
                          key={prompt.label}
                          className="text-left text-[11px] font-sans text-muted-foreground bg-accent/10 px-3 py-2 rounded border border-border/30 flex items-center justify-between"
                          aria-disabled="true"
                        >
                          <span>{prompt.label}</span>
                          <span className="text-[9px] font-mono uppercase text-amber-500">full chat approval</span>
                        </div>
                      )
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ScrollArea>

        <div className="p-4 border-t border-border/40 bg-background/30 space-y-3 shrink-0">
          <Link
            href={defaultChatHref}
            className="relative block rounded-lg border border-border/60 bg-card/50 p-3 pr-12 min-h-[80px] hover:border-cyan-500/50 transition-colors"
            aria-label="Open full chat with Home context"
          >
            <div className="text-[13px] font-sans min-h-[54px] text-foreground/90">
              {defaultPrompt}
            </div>
            <div className="absolute bottom-3 right-3 flex items-center gap-2">
              <Paperclip className="w-4 h-4 text-muted-foreground" />
              <div className="w-7 h-7 bg-cyan-600 rounded flex items-center justify-center">
                <Send className="w-3.5 h-3.5 text-white" />
              </div>
            </div>
          </Link>
          <div className="flex items-center justify-between px-1">
            <span className="text-[10px] font-mono text-muted-foreground flex items-center gap-1.5 uppercase">
              <Sparkles className="w-3 h-3 text-cyan-500" />
              Opens Full Chat Draft
            </span>
            <span className="text-[10px] font-mono text-muted-foreground/40 italic uppercase">
              No Home-side execution
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function buildChatHandoffHref(prompt: string, attachedItem: NewsItem | null): string {
  const params = new URLSearchParams({ prompt });
  if (attachedItem?.sourceId && attachedItem.sourceKind && attachedItem.resolvable && !attachedItem.chatBlockedReason) {
    params.set('source_id', attachedItem.sourceId);
    params.set('source_kind', attachedItem.sourceKind);
    params.set('source_title', attachedItem.headline);
  }
  return `/full-chat?${params.toString()}`;
}
