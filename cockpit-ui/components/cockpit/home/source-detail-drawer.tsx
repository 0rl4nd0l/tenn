'use client'

import { useEffect, useState } from 'react';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription, DrawerFooter } from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';
import { NewsItem } from '@/types/cockpit-home';
import { EvidenceBadge } from './evidence-badge';
import { AlertCircle, Database, ExternalLink, Loader2, MessageSquare, ShieldCheck } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface SourceDetailDrawerProps {
  item: NewsItem | null;
  isOpen: boolean;
  onClose: () => void;
  onAnalyze: (item: NewsItem) => void;
}

type SourceDetailState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; payload: SourceDetailPayload }
  | { status: 'error'; message: string };

interface SourceDetailPayload {
  ok?: boolean;
  source_id?: string;
  source_status?: string;
  source_name?: string;
  published_at?: string;
  chunk_count?: number;
  memo_status?: string;
  takeaway_source?: string;
  takeaways?: SourceTakeaway[];
  model?: string;
  prompt_version?: string;
}

interface SourceTakeaway {
  text?: string;
}

export function SourceDetailDrawer({ item, isOpen, onClose, onAnalyze }: SourceDetailDrawerProps) {
  const [sourceDetail, setSourceDetail] = useState<SourceDetailState>({ status: 'idle' });

  useEffect(() => {
    if (!isOpen || !item?.sourceId || !item.resolvable || item.isDemo) {
      setSourceDetail({ status: 'idle' });
      return;
    }

    const sourceId = item.sourceId;
    const controller = new AbortController();
    setSourceDetail({ status: 'loading' });

    async function loadSourceDetail() {
      try {
        const response = await fetch('/api/cockpit/commentary/takeaways', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source_id: sourceId, limit: 3 }),
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = (await response.json()) as SourceDetailPayload;
        setSourceDetail({ status: 'ready', payload });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setSourceDetail({
          status: 'error',
          message: error instanceof Error ? error.message : 'Source detail request failed',
        });
      }
    }

    void loadSourceDetail();

    return () => controller.abort();
  }, [isOpen, item?.isDemo, item?.resolvable, item?.sourceId]);

  if (!item) return null;

  const dataState = item.dataState ?? (item.isDemo ? 'DATA_MISSING' : 'READY');
  const sourceLabels = item.evidenceLabels?.length ? item.evidenceLabels : [item.sourceLabel ?? null].filter(Boolean);
  const canAnalyze = Boolean(item.resolvable && item.sourceId && !item.chatBlockedReason && !item.isDemo);

  return (
    <Drawer open={isOpen} onClose={onClose}>
      <DrawerContent className="bg-background border-t border-border max-h-[90vh]">
        <div className="mx-auto w-full max-w-4xl">
          <DrawerHeader className="border-b border-border/40 pb-6">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <span className="text-[12px] font-mono font-bold text-cyan-500 px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded uppercase">
                  {item.ticker || 'NO_TICKER'}
                </span>
                <EvidenceBadge level={item.trustLevel} className="scale-110" />
              </div>
              <span className="text-[11px] font-mono text-muted-foreground uppercase">{item.timestamp}</span>
            </div>
            <DrawerTitle className="text-xl font-sans font-bold leading-tight text-foreground">
              {item.headline}
            </DrawerTitle>
            <DrawerDescription className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground/70 mt-1">
              Source: {item.source} | ID: {item.id}
            </DrawerDescription>
          </DrawerHeader>

          <ScrollArea className="px-6 py-6 h-[400px]">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="md:col-span-2 space-y-6">
                <section>
                  <h5 className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                    <Database className="w-3 h-3" />
                    BFF Source Identity
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-card/40 p-4 rounded-lg border border-border/40">
                    <MetadataField label="Data State" value={dataState} emphasis={stateTone(dataState)} />
                    <MetadataField label="Source Label" value={item.sourceLabel ?? 'unknown_unclassified'} />
                    <MetadataField label="Source ID" value={item.sourceId || 'DATA_MISSING'} />
                    <MetadataField label="Source Kind" value={item.sourceKind || 'DATA_MISSING'} />
                    <MetadataField label="Resolver" value={item.resolver || 'none'} />
                    <MetadataField label="Resolvable" value={item.resolvable ? 'true' : 'false'} />
                  </div>
                </section>

                <section>
                  <h5 className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                    <ShieldCheck className="w-3 h-3" />
                    Evidence Labels
                  </h5>
                  <div className="flex flex-wrap gap-2 bg-accent/10 p-4 rounded-lg border border-border/40">
                    {sourceLabels.length > 0 ? (
                      sourceLabels.map((label) => (
                        <span
                          key={label}
                          className="text-[10px] font-mono uppercase px-2 py-1 rounded border border-border bg-background/50 text-muted-foreground"
                        >
                          {label}
                        </span>
                      ))
                    ) : (
                      <span className="text-[11px] font-mono text-amber-500">DATA_MISSING</span>
                    )}
                  </div>
                </section>

                {(item.isDemo || item.dataMissing?.length || item.chatBlockedReason) && (
                  <section>
                    <h5 className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-3 flex items-center gap-2">
                      <AlertCircle className="w-3 h-3" />
                      Limits
                    </h5>
                    <div className="space-y-2 bg-amber-500/5 p-4 rounded-lg border border-amber-500/20">
                      {item.isDemo && (
                        <p className="text-[12px] font-sans text-amber-500">
                          Demo fixture only. This item is not source-backed and cannot be attached as evidence.
                        </p>
                      )}
                      {item.chatBlockedReason && (
                        <p className="text-[12px] font-sans text-amber-500">
                          Chat handoff blocked: {item.chatBlockedReason}.
                        </p>
                      )}
                      {item.dataMissing?.map((signal) => (
                        <div key={`${signal.section}:${signal.code}`} className="text-[11px] font-mono text-muted-foreground">
                          <span className="text-amber-500">{signal.code}</span>: {signal.message}
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>

              <div className="space-y-6">
                <section>
                  <h5 className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-3">
                    Source Access
                  </h5>
                  <SourceAccessPanel state={sourceDetail} sourceId={item.sourceId} />
                </section>
              </div>
            </div>
          </ScrollArea>

          <DrawerFooter className="border-t border-border/40 py-6 flex-row gap-4">
            <Button
              variant="outline"
              size="sm"
              className="font-mono text-[11px]"
              disabled={!item.sourceUrl}
              asChild={Boolean(item.sourceUrl)}
            >
              {item.sourceUrl ? (
                <a href={item.sourceUrl} target="_blank" rel="noreferrer">
                  OPEN ORIGINAL SOURCE
                  <ExternalLink className="w-3 h-3 ml-2" />
                </a>
              ) : (
                <span className="inline-flex items-center">
                  ORIGINAL SOURCE DATA_MISSING
                  <ExternalLink className="w-3 h-3 ml-2" />
                </span>
              )}
            </Button>
            <Button
              className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white font-mono uppercase tracking-tighter disabled:opacity-50"
              disabled={!canAnalyze}
              onClick={() => {
                if (canAnalyze) {
                  onAnalyze(item);
                }
              }}
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

function SourceAccessPanel({
  state,
  sourceId,
}: {
  state: SourceDetailState;
  sourceId?: string | null;
}) {
  if (!sourceId) {
    return (
      <div className="text-[11px] font-sans text-muted-foreground leading-relaxed bg-card/30 rounded border border-border/30 p-3">
        Source detail DATA_MISSING: this Home item did not include a backend source_id.
      </div>
    );
  }

  if (state.status === 'loading') {
    return (
      <div className="flex items-center gap-2 text-[11px] font-sans text-muted-foreground bg-card/30 rounded border border-border/30 p-3">
        <Loader2 className="w-3 h-3 animate-spin text-cyan-500" />
        Loading source detail.
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="text-[11px] font-sans text-amber-500 leading-relaxed bg-amber-500/5 rounded border border-amber-500/20 p-3">
        Source detail DATA_MISSING: {state.message}.
      </div>
    );
  }

  if (state.status !== 'ready') {
    return (
      <div className="text-[11px] font-sans text-muted-foreground leading-relaxed bg-card/30 rounded border border-border/30 p-3">
        Source detail is available for backend-resolvable Home commentary sources.
      </div>
    );
  }

  const payload = state.payload;
  const takeaways = (payload.takeaways ?? []).filter((takeaway) => takeaway.text);

  return (
    <div className="space-y-3 bg-card/30 rounded border border-border/30 p-3">
      <div className="grid grid-cols-2 gap-3">
        <MetadataField label="Source Status" value={payload.source_status || 'DATA_MISSING'} />
        <MetadataField label="Chunks" value={typeof payload.chunk_count === 'number' ? String(payload.chunk_count) : 'DATA_MISSING'} />
        <MetadataField label="Memo" value={payload.memo_status || 'DATA_MISSING'} />
        <MetadataField label="Takeaways" value={payload.takeaway_source || 'DATA_MISSING'} />
      </div>

      {takeaways.length > 0 ? (
        <div className="space-y-2">
          {takeaways.map((takeaway, index) => (
            <div key={`${payload.source_id ?? sourceId}:takeaway:${index}`} className="text-[11px] font-sans text-muted-foreground leading-relaxed border-t border-border/30 pt-2">
              {takeaway.text}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[11px] font-sans text-amber-500 border-t border-border/30 pt-2">
          Source detail returned no takeaways.
        </div>
      )}
    </div>
  );
}

function MetadataField({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: string;
  emphasis?: 'normal' | 'warning' | 'error';
}) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <span className="text-[10px] font-mono text-muted-foreground/60 uppercase">{label}</span>
      <span
        className={cn(
          'text-[12px] font-mono font-bold break-words',
          emphasis === 'warning' && 'text-amber-500',
          emphasis === 'error' && 'text-red-500',
          (!emphasis || emphasis === 'normal') && 'text-foreground',
        )}
      >
        {value}
      </span>
    </div>
  );
}

function stateTone(state: string): 'normal' | 'warning' | 'error' {
  if (state === 'DATA_MISSING') {
    return 'error';
  }
  if (state === 'PARTIAL' || state === 'DEGRADED') {
    return 'warning';
  }
  return 'normal';
}
