'use client'

import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription, DrawerFooter } from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';
import { NewsItem } from '@/types/cockpit-home';
import { EvidenceBadge } from './evidence-badge';
import { ExternalLink, MessageSquare, ShieldCheck, Database, History, Share2 } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

interface SourceDetailDrawerProps {
  item: NewsItem | null;
  isOpen: boolean;
  onClose: () => void;
  onAnalyze: (item: NewsItem) => void;
}

export function SourceDetailDrawer({ item, isOpen, onClose, onAnalyze }: SourceDetailDrawerProps) {
  if (!item) return null;

  return (
    <Drawer open={isOpen} onClose={onClose}>
      <DrawerContent className="bg-background border-t border-border max-h-[90vh]">
        <div className="mx-auto w-full max-w-4xl">
          <DrawerHeader className="border-b border-border/40 pb-6">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <span className="text-[12px] font-mono font-bold text-cyan-500 px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded uppercase">
                  {item.ticker}
                </span>
                <EvidenceBadge level={item.trustLevel} className="scale-110" />
              </div>
              <span className="text-[11px] font-mono text-muted-foreground uppercase">{item.timestamp}</span>
            </div>
            <DrawerTitle className="text-xl font-sans font-bold leading-tight text-foreground">
              {item.headline}
            </DrawerTitle>
            <DrawerDescription className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground/70 mt-1">
              Source: {item.source} • ID: {item.id}
            </DrawerDescription>
          </DrawerHeader>

          <ScrollArea className="px-6 py-6 h-[400px]">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="md:col-span-2 space-y-6">
                <section>
                  <h5 className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                    <Database className="w-3 h-3" />
                    Ingestion Metadata
                  </h5>
                  <div className="grid grid-cols-2 gap-4 bg-card/40 p-4 rounded-lg border border-border/40">
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-mono text-muted-foreground/60 uppercase">Entity Linking</span>
                      <span className="text-[12px] font-mono text-green-500 font-bold">VERIFIED</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-mono text-muted-foreground/60 uppercase">Index State</span>
                      <span className="text-[12px] font-mono text-cyan-500 font-bold">OPTIMIZED</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-mono text-muted-foreground/60 uppercase">Evidence State</span>
                      <span className="text-[12px] font-mono text-foreground font-bold italic">EVIDENCE-READY</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-mono text-muted-foreground/60 uppercase">Materiality Score</span>
                      <span className="text-[12px] font-mono text-amber-500 font-bold">HIGH (PENDING)</span>
                    </div>
                  </div>
                </section>

                <section>
                  <h5 className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                    <ShieldCheck className="w-3 h-3" />
                    Source Context
                  </h5>
                  <p className="text-[13px] font-sans text-muted-foreground leading-relaxed bg-accent/10 p-4 rounded-lg border-l-2 border-l-cyan-500/30">
                    This source was discovered via the ASX real-time stream. It indicates a potential logistics acquisition in the European market. Initial entity linking confirms <strong>&quot;WTC&quot;</strong> as the primary subject. Ingestion completed at 10:31:04 AM.
                  </p>
                </section>
              </div>

              <div className="space-y-6">
                <section>
                  <h5 className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                    <History className="w-3 h-3" />
                    Related Events
                  </h5>
                  <div className="space-y-2">
                    <div className="text-[11px] font-mono p-2 bg-card/30 rounded border border-border/20 hover:border-cyan-500/30 cursor-pointer">
                      WTC Earnings Call (Prior)
                    </div>
                    <div className="text-[11px] font-mono p-2 bg-card/30 rounded border border-border/20 hover:border-cyan-500/30 cursor-pointer">
                      Logistics M&A Trends Q1
                    </div>
                  </div>
                </section>

                <div className="flex flex-col gap-2 pt-4">
                  <Button variant="outline" size="sm" className="w-full font-mono text-[11px] justify-between">
                    OPEN ORIGINAL SOURCE
                    <ExternalLink className="w-3 h-3" />
                  </Button>
                  <Button variant="outline" size="sm" className="w-full font-mono text-[11px] justify-between">
                    SHARE CONTEXT
                    <Share2 className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </div>
          </ScrollArea>

          <DrawerFooter className="border-t border-border/40 py-6 flex-row gap-4">
            <Button
              className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white font-mono uppercase tracking-tighter"
              onClick={() => onAnalyze(item)}
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Analyze with Tenn Assistant
            </Button>
            <Button variant="ghost" onClick={onClose} className="font-mono uppercase text-[11px]">
              Dismiss
            </Button>
          </DrawerFooter>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
