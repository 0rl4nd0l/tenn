'use client';

import { useEffect, useMemo, useState } from 'react';
import { FileSearch, Loader2, ShieldAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type {
  StrategyLabArtifactsResponse,
  StrategyLabReviewArtifact,
  StrategyLabReviewEvidenceKind,
} from '@/lib/strategy-lab-artifacts';
import { cn } from '@/lib/utils';

type StrategyLabArtifactsCardState =
  | { status: 'loading' }
  | { status: 'ready'; payload: StrategyLabArtifactsResponse }
  | { status: 'error'; message: string };

export function StrategyLabArtifactsReviewCard() {
  const [state, setState] = useState<StrategyLabArtifactsCardState>({ status: 'loading' });

  useEffect(() => {
    const controller = new AbortController();

    async function loadArtifacts() {
      try {
        const response = await fetch('/api/cockpit/strategy-lab/artifacts', {
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = (await response.json()) as StrategyLabArtifactsResponse;
        setState({ status: 'ready', payload });
      } catch (error) {
        if (controller.signal.aborted) return;
        setState({
          status: 'error',
          message: error instanceof Error ? error.message : 'Strategy Lab artifact route failed',
        });
      }
    }

    void loadArtifacts();

    return () => controller.abort();
  }, []);

  if (state.status === 'loading') {
    return (
      <Card className="terminal-panel" data-testid="strategy-lab-artifacts-review-card">
        <CardContent className="p-4 flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-cyan-500 animate-spin" />
          <div>
            <div className="text-[12px] font-mono font-bold uppercase">Artifact Review</div>
            <div className="text-[11px] text-muted-foreground">Loading repo-only artifacts</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (state.status === 'error') {
    return (
      <Card
        className="terminal-panel border-amber-500/30"
        data-testid="strategy-lab-artifacts-review-card"
      >
        <CardContent className="p-4 flex items-center gap-3">
          <ShieldAlert className="w-4 h-4 text-amber-500" />
          <div>
            <div className="text-[12px] font-mono font-bold uppercase">Artifact Review DATA_MISSING</div>
            <div className="text-[11px] text-muted-foreground">Artifact route unavailable: {state.message}</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return <ReadyStrategyLabArtifactsReviewCard payload={state.payload} />;
}

function ReadyStrategyLabArtifactsReviewCard({ payload }: { payload: StrategyLabArtifactsResponse }) {
  const counts = useMemo(() => {
    return payload.artifacts.reduce(
      (acc, artifact) => {
        if (artifact.availability === 'available') {
          acc.available += 1;
        }
        if (artifact.authoritative) {
          acc.authoritative += 1;
        }
        return acc;
      },
      { available: 0, authoritative: 0 },
    );
  }, [payload.artifacts]);

  return (
    <Card className="terminal-panel" data-testid="strategy-lab-artifacts-review-card">
      <CardHeader className="py-3 px-4 flex flex-row items-start justify-between gap-4 space-y-0 border-b border-border/40">
        <div className="min-w-0">
          <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <FileSearch className="w-3.5 h-3.5" />
            Strategy Lab Artifact Review
          </CardTitle>
          <p className="mt-2 text-[12px] text-foreground leading-snug">
            Repo-only evidence list for existing Strategy Lab artifacts and reports.
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <Badge variant="outline" className="border-emerald-500/40 text-emerald-300 bg-emerald-500/10">
            READ ONLY
          </Badge>
          <Badge variant="outline" className="border-amber-500/40 text-amber-300 bg-amber-500/10">
            NO STORE WRITES
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-4 grid gap-4">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <MetricPill label="available" value={`${counts.available}/${payload.artifacts.length}`} />
          <MetricPill label="artifact_v1" value={`${counts.authoritative}`} />
          <MetricPill label="source mode" value="repo-only" />
          <MetricPill label="review" value="PENDING" />
        </div>

        <div className="grid gap-3">
          {payload.artifacts.map((artifact) => (
            <ArtifactReviewRow key={artifact.id} artifact={artifact} />
          ))}
        </div>

        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
          <div className="text-[10px] font-mono uppercase text-amber-300">DATA_MISSING</div>
          <div className="mt-1 text-[11px] text-muted-foreground leading-relaxed">
            {payload.data_missing[0]}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ArtifactReviewRow({ artifact }: { artifact: StrategyLabReviewArtifact }) {
  const firstDataMissing = artifact.data_missing[0] ?? 'DATA_MISSING';
  const status = artifact.review_status === 'DATA_MISSING' ? 'DATA_MISSING' : artifact.review_status;

  return (
    <div className="rounded-md border border-border/50 bg-background/40 p-3">
      <div className="grid gap-3 lg:grid-cols-[1fr_1.4fr]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[12px] font-semibold text-foreground">{artifact.label}</span>
            <Badge
              variant="outline"
              className={cn(
                'text-[9px] font-mono uppercase',
                artifact.authoritative
                  ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                  : 'border-amber-500/40 text-amber-300 bg-amber-500/10',
              )}
            >
              {artifact.authoritative ? 'strategy_lab_artifact_v1' : evidenceKindLabel(artifact.evidence_kind)}
            </Badge>
          </div>

          <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] font-mono uppercase text-muted-foreground sm:grid-cols-4">
            <span>{artifact.artifact_type}</span>
            <span>{status}</span>
            <span>{artifact.availability}</span>
            <span>{artifact.canonical_financial_truth === false ? 'NO CANONICAL TRUTH' : 'DATA_MISSING'}</span>
          </div>

          <div className="mt-2 grid gap-1 break-all text-[10px] text-muted-foreground">
            <div>
              <span className="font-mono uppercase text-muted-foreground/80">Source: </span>
              {artifact.source_path}
            </div>
            <div>
              <span className="font-mono uppercase text-muted-foreground/80">Report: </span>
              {artifact.source_report_path}
            </div>
          </div>
        </div>

        <div className="grid gap-2 text-[11px] leading-relaxed text-muted-foreground">
          <div>
            <span className="font-mono uppercase text-emerald-300">Proves: </span>
            {artifact.what_it_proves[0]}
          </div>
          <div>
            <span className="font-mono uppercase text-amber-300">Does not prove: </span>
            {artifact.what_it_does_not_prove[0]}
          </div>
          <div>
            <span className="font-mono uppercase text-amber-300">DATA_MISSING: </span>
            {firstDataMissing}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/50 bg-background/40 px-3 py-2">
      <div className="text-[9px] font-mono uppercase text-muted-foreground">{label}</div>
      <div className="mt-1 text-[12px] font-mono uppercase text-foreground">{value}</div>
    </div>
  );
}

function evidenceKindLabel(kind: StrategyLabReviewEvidenceKind) {
  switch (kind) {
    case 'helper_pre_envelope':
      return 'helper/pre-envelope';
    case 'report_evidence':
      return 'report evidence';
    case 'strategy_lab_artifact_v1':
      return 'strategy_lab_artifact_v1';
  }
}
