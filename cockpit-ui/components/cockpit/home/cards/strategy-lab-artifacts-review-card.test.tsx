import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { buildStrategyLabArtifactsResponse } from '@/lib/strategy-lab-artifacts';
import { StrategyLabArtifactsReviewCard } from './strategy-lab-artifacts-review-card';

describe('StrategyLabArtifactsReviewCard', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders a repo-only artifact review list without implying live transport', async () => {
    const payload = buildStrategyLabArtifactsResponse({
      generatedAt: '2026-05-24T00:00:00.000Z',
      artifacts: [
        {
          id: 'artifact_v1_backtest_fixture',
          label: 'Backtest artifact fixture',
          evidence_kind: 'strategy_lab_artifact_v1',
          authoritative: true,
          availability: 'available',
          source_path: 'docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json',
          source_report_path: 'reports/agent_jobs/source_report',
          preserved_commit: 'DATA_MISSING',
          preserved_subject: 'DATA_MISSING',
          historical_status: 'DATA_MISSING',
          current_runtime_available: 'DATA_MISSING',
          paper_order_placement: 'DATA_MISSING',
          schema_version: 'strategy_lab_artifact_v1',
          artifact_id: 'stratlab_backtest_run_fixture',
          artifact_type: 'backtest_run',
          review_status: 'PENDING_REVIEW',
          result_status: 'SUCCEEDED',
          canonical_financial_truth: false,
          execution_allowed: false,
          store_writes: false,
          what_it_proves: ['A parseable strategy_lab_artifact_v1 backtest_run fixture exists in the repo.'],
          what_it_does_not_prove: ['It does not prove live QuantDinger transport is available.'],
          data_missing: ['live_sidecar_transport'],
        },
        {
          id: 'phase2_helper_backtest',
          label: 'Phase 2 helper backtest evidence',
          evidence_kind: 'helper_pre_envelope',
          authoritative: false,
          availability: 'available',
          source_path:
            'reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/backtest_run.json',
          source_report_path: 'DATA_MISSING',
          preserved_commit: '0ee837f7dc0706f1b0ff6d6c900522f4c2b43090',
          preserved_subject: 'milestone(reporting): preserve quantdinger readonly smoke proof',
          historical_status: 'historical_smoke_proof',
          current_runtime_available: false,
          paper_order_placement: false,
          schema_version: 'strategy_lab_sidecar_artifact_v1',
          artifact_id: 'strategy_lab.quantdinger.backtest_run',
          artifact_type: 'backtest_run',
          review_status: 'PENDING_REVIEW',
          result_status: 'SUCCEEDED',
          canonical_financial_truth: false,
          execution_allowed: false,
          store_writes: false,
          what_it_proves: ['A Phase 2 normalized sidecar helper artifact exists.'],
          what_it_does_not_prove: ['It is helper evidence, not the authoritative envelope.'],
          data_missing: ['strategy_lab_artifact_v1_envelope'],
        },
      ],
    });
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    render(<StrategyLabArtifactsReviewCard />);

    expect(await screen.findByText('Strategy Lab Artifact Review')).toBeInTheDocument();
    expect(screen.getByText('READ ONLY')).toBeInTheDocument();
    expect(screen.getByText('NO STORE WRITES')).toBeInTheDocument();
    expect(screen.getByText('Backtest artifact fixture')).toBeInTheDocument();
    expect(screen.getByText('Phase 2 helper backtest evidence')).toBeInTheDocument();
    expect(screen.getByText('reports/agent_jobs/source_report')).toBeInTheDocument();
    expect(screen.getByText('helper/pre-envelope')).toBeInTheDocument();
    expect(screen.getByText('historical smoke proof')).toBeInTheDocument();
    expect(screen.getByText('0ee837f7dc0706f1b0ff6d6c900522f4c2b43090')).toBeInTheDocument();
    expect(screen.getByText('offline')).toBeInTheDocument();
    expect(screen.getByText(/It does not prove live QuantDinger transport/)).toBeInTheDocument();
    expect(screen.getAllByText('DATA_MISSING').length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/strategy-lab/artifacts',
      expect.objectContaining({ cache: 'no-store' }),
    );
  });
});
