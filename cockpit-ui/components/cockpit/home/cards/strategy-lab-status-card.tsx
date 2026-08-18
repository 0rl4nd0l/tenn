'use client';

import { useEffect, useState } from 'react';
import { ArrowUpRight, Ban, FlaskConical, Loader2, ShieldAlert, ShieldCheck } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  buildStrategyLabHomeSummary,
  type StrategyLabHomeSummary,
  type StrategyLabStatusResponse,
} from '@/lib/strategy-lab-status';
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
  const summary = buildStrategyLabHomeSummary(payload);

  return (
    <Card className="terminal-panel" data-testid="strategy-lab-status-card">
      <CardHeader className="py-3 px-4 flex flex-row items-start justify-between gap-4 space-y-0 border-b border-border/40">
        <div className="min-w-0">
          <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <FlaskConical className="w-3.5 h-3.5" />
            Strategy Lab
          </CardTitle>
          <p className="mt-2 text-[13px] text-foreground leading-snug">{summary.valueSummary}</p>
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-2">
          <Badge variant="outline" className="border-emerald-500/40 text-emerald-300 bg-emerald-500/10">
            Proof verified
          </Badge>
          <Badge variant="outline" className="border-amber-500/40 text-amber-400 bg-amber-500/10">
            Pending review
          </Badge>
          <Badge variant="outline" className="border-zinc-500/40 text-zinc-300 bg-zinc-500/10">
            Offline
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-4 grid gap-4 lg:grid-cols-[1.4fr_0.9fr]">
        <div className="grid gap-4" data-testid="strategy-lab-home-summary">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <StatusMetric label="Status" value={summary.status} tone="emerald" />
            <StatusMetric label="Current runtime" value={summary.currentRuntime} tone="zinc" />
            <StatusMetric label="Review state" value={summary.reviewState} tone="amber" />
            <StatusMetric label="Trading/execution" value={summary.tradingExecution} tone="amber" />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3">
              <div className="flex items-start gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-300 mt-0.5 shrink-0" />
                <div>
                  <div className="text-[10px] font-mono uppercase text-emerald-300">Value</div>
                  <div className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                    Use as reviewable sandbox evidence only; it does not create a current sidecar or trading surface.
                  </div>
                </div>
              </div>
            </div>
            <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
              <div className="flex items-start gap-2">
                <Ban className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-[10px] font-mono uppercase text-amber-300">Blocker</div>
                  <div className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                    {summary.blockerSummary}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-2 text-[11px] leading-relaxed text-muted-foreground md:grid-cols-3">
            <CompactProofCount label="Proof files" available={summary.availableEvidenceCount} total={summary.totalEvidenceCount} />
            <CompactProofCount label="Baseline artifacts" available={summary.availableArtifactCount} total={summary.totalArtifactCount} />
            <div className="rounded-md border border-border/50 bg-background/40 p-3">
              <div className="text-[9px] font-mono uppercase text-muted-foreground">Runtime note</div>
              <div className="mt-1">Current sidecar runtime is offline; no live transport is integrated.</div>
            </div>
          </div>
        </div>

        <div className="flex flex-col justify-between gap-3 rounded-md border border-border/50 bg-background/40 p-3">
          <div>
            <div className="text-[10px] font-mono uppercase text-muted-foreground">Drilldown</div>
            <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
              Detailed payload refs, artifact paths, review rows, export packets, and DATA_MISSING lists are kept out
              of the Home summary.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="sm" className="h-8 text-[11px]">
              <a href={summary.detailRoute} target="_blank" rel="noreferrer">
                <ArrowUpRight className="w-3.5 h-3.5" />
                View details
              </a>
            </Button>
            <Button asChild variant="ghost" size="sm" className="h-8 text-[11px]">
              <a href={summary.statusRoute} target="_blank" rel="noreferrer">
                Open Strategy Lab
              </a>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: StrategyLabHomeSummary[keyof Pick<
    StrategyLabHomeSummary,
    'status' | 'currentRuntime' | 'reviewState' | 'tradingExecution'
  >];
  tone: 'emerald' | 'amber' | 'zinc';
}) {
  return (
    <div
      className={cn(
        'min-h-16 rounded-md border px-3 py-2',
        tone === 'emerald' && 'border-emerald-500/30 bg-emerald-500/5',
        tone === 'amber' && 'border-amber-500/30 bg-amber-500/5',
        tone === 'zinc' && 'border-zinc-500/30 bg-zinc-500/5',
      )}
    >
      <div className="text-[9px] font-mono uppercase text-muted-foreground">{label}</div>
      <div
        className={cn(
          'mt-1 text-[12px] font-semibold leading-snug',
          tone === 'emerald' && 'text-emerald-300',
          tone === 'amber' && 'text-amber-300',
          tone === 'zinc' && 'text-zinc-300',
        )}
      >
        {value}
      </div>
    </div>
  );
}

function CompactProofCount({ label, available, total }: { label: string; available: number; total: number }) {
  return (
    <div className="rounded-md border border-border/50 bg-background/40 p-3">
      <div className="text-[9px] font-mono uppercase text-muted-foreground">{label}</div>
      <div className="mt-1 text-[12px] font-mono uppercase text-foreground">
        {available}/{total} available
      </div>
    </div>
  );
}
