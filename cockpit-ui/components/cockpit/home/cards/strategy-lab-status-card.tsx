'use client';

import { useEffect, useMemo, useState } from 'react';
import { Ban, FileCheck2, FlaskConical, Loader2, ShieldAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { StrategyLabStatusResponse } from '@/lib/strategy-lab-status';
import { cn } from '@/lib/utils';

type StrategyLabCardState =
  | { status: 'loading' }
  | { status: 'ready'; payload: StrategyLabStatusResponse }
  | { status: 'error'; message: string };

export function StrategyLabStatusCard() {
  const [state, setState] = useState<StrategyLabCardState>({ status: 'loading' });

  useEffect(() => {
    const controller = new AbortController();

    async function loadStatus() {
      try {
        const response = await fetch('/api/cockpit/strategy-lab/status', {
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = (await response.json()) as StrategyLabStatusResponse;
        setState({ status: 'ready', payload });
      } catch (error) {
        if (controller.signal.aborted) return;
        setState({
          status: 'error',
          message: error instanceof Error ? error.message : 'Strategy Lab status route failed',
        });
      }
    }

    void loadStatus();

    return () => controller.abort();
  }, []);

  if (state.status === 'loading') {
    return (
      <Card className="terminal-panel" data-testid="strategy-lab-status-card">
        <CardContent className="p-4 flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-cyan-500 animate-spin" />
          <div>
            <div className="text-[12px] font-mono font-bold uppercase">Strategy Lab</div>
            <div className="text-[11px] text-muted-foreground">Loading read-only status</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (state.status === 'error') {
    return (
      <Card className="terminal-panel border-amber-500/30" data-testid="strategy-lab-status-card">
        <CardContent className="p-4 flex items-center gap-3">
          <ShieldAlert className="w-4 h-4 text-amber-500" />
          <div>
            <div className="text-[12px] font-mono font-bold uppercase">Strategy Lab DATA_MISSING</div>
            <div className="text-[11px] text-muted-foreground">Status route unavailable: {state.message}</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return <ReadyStrategyLabStatusCard payload={state.payload} />;
}

function ReadyStrategyLabStatusCard({ payload }: { payload: StrategyLabStatusResponse }) {
  const availableArtifacts = useMemo(
    () => payload.artifact_refs.filter((artifact) => artifact.availability === 'available'),
    [payload.artifact_refs],
  );
  const keyCapabilities = payload.capability_status.slice(0, 4);
  const quantdinger = payload.quantdinger_status;

  return (
    <Card className="terminal-panel" data-testid="strategy-lab-status-card">
      <CardHeader className="py-3 px-4 flex flex-row items-start justify-between gap-4 space-y-0 border-b border-border/40">
        <div className="min-w-0">
          <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <FlaskConical className="w-3.5 h-3.5" />
            Strategy Lab / QuantDinger
          </CardTitle>
          <p className="mt-2 text-[13px] text-foreground leading-snug">{payload.headline}</p>
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-2">
          <Badge variant="outline" className="border-cyan-500/40 text-cyan-300 bg-cyan-500/10">
            HISTORICAL SMOKE PASSED
          </Badge>
          <Badge variant="outline" className="border-amber-500/40 text-amber-400 bg-amber-500/10">
            PENDING REVIEW
          </Badge>
          <Badge variant="outline" className="border-zinc-500/40 text-zinc-300 bg-zinc-500/10">
            CURRENT SIDECAR OFFLINE
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-7">
            <BoundaryPill label="READ ONLY" active={payload.boundary_flags.read_only} />
            <BoundaryPill label="CURRENT SIDECAR OFFLINE" active={!quantdinger.current_sidecar_available} />
            <BoundaryPill label="NO LIVE TRADING" active={!payload.boundary_flags.live_trading} />
            <BoundaryPill label="NO PAPER ORDER PLACEMENT" active={!quantdinger.paper_order_placement} />
            <BoundaryPill label="NO REAL TRANSPORT" active={!payload.boundary_flags.real_transport} />
            <BoundaryPill label="NO STORE WRITES" active={!payload.boundary_flags.store_writes} />
            <BoundaryPill
              label="NO CANONICAL FINANCIAL TRUTH"
              active={!payload.boundary_flags.canonical_financial_truth}
            />
          </div>

          <div className="rounded-md border border-cyan-500/30 bg-cyan-500/5 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-[10px] font-mono uppercase text-cyan-300">Read-only smoke history</div>
              <div className="text-[10px] font-mono uppercase text-muted-foreground">
                {quantdinger.last_readonly_sidecar_smoke_review_status}
              </div>
            </div>
            <div className="mt-2 grid gap-1 text-[10px] leading-relaxed text-muted-foreground">
              <div>
                <span className="font-mono uppercase text-muted-foreground/80">Verdict: </span>
                {quantdinger.last_readonly_sidecar_smoke}
              </div>
              <div className="break-all">
                <span className="font-mono uppercase text-muted-foreground/80">Commit: </span>
                {quantdinger.last_readonly_sidecar_smoke_commit}
              </div>
              <div>
                <span className="font-mono uppercase text-muted-foreground/80">Runtime: </span>
                {quantdinger.sidecar_runtime_state}
              </div>
            </div>
          </div>

          <div className="rounded-md border border-border/50 bg-background/40 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-[10px] font-mono uppercase text-muted-foreground">Baseline artifacts</div>
              <div className="text-[10px] font-mono text-cyan-400">
                {availableArtifacts.length}/{payload.artifact_refs.length} available
              </div>
            </div>
            <div className="mt-3 grid gap-2">
              {payload.artifact_refs.slice(0, 4).map((artifact) => (
                <div key={artifact.id} className="grid grid-cols-[auto_1fr_auto] items-center gap-2 text-[11px]">
                  <FileCheck2
                    className={cn(
                      'w-3.5 h-3.5',
                      artifact.availability === 'available' ? 'text-emerald-400' : 'text-muted-foreground',
                    )}
                  />
                  <span className="truncate text-foreground">{artifact.label}</span>
                  <span
                    className={cn(
                      'font-mono uppercase',
                      artifact.availability === 'available' ? 'text-emerald-400' : 'text-amber-400',
                    )}
                  >
                    {artifact.availability}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-3">
          <div className="rounded-md border border-border/50 bg-background/40 p-3">
            <div className="text-[10px] font-mono uppercase text-muted-foreground">Capability state</div>
            <div className="mt-3 grid gap-2">
              {keyCapabilities.map((capability) => (
                <div key={capability.id} className="flex items-start gap-2">
                  <span className={cn('mt-1 w-1.5 h-1.5 rounded-full shrink-0', capabilityDot(capability.state))} />
                  <div className="min-w-0">
                    <div className="text-[11px] font-semibold text-foreground">{capability.label}</div>
                    <div className="text-[10px] leading-relaxed text-muted-foreground">{capability.summary}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
            <Ban className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
            <div>
              <div className="text-[10px] font-mono uppercase text-amber-300">DATA_MISSING</div>
              <div className="text-[11px] text-muted-foreground leading-relaxed">
                {payload.data_missing[0] ?? 'Strategy Lab evidence is incomplete.'}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function BoundaryPill({ label, active }: { label: string; active: boolean }) {
  return (
    <div
      className={cn(
        'min-h-11 rounded-md border px-2.5 py-2 flex items-center text-[9px] font-mono uppercase leading-tight',
        active
          ? 'border-emerald-500/30 bg-emerald-500/5 text-emerald-300'
          : 'border-amber-500/30 bg-amber-500/5 text-amber-300',
      )}
    >
      {label}
    </div>
  );
}

function capabilityDot(state: StrategyLabStatusResponse['capability_status'][number]['state']) {
  switch (state) {
    case 'present_offline':
      return 'bg-cyan-400';
    case 'forbidden':
      return 'bg-amber-400';
    case 'absent':
      return 'bg-zinc-500';
    case 'data_missing':
      return 'bg-red-400';
  }
}
