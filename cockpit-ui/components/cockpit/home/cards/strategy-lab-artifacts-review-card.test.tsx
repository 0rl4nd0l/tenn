import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { buildStrategyLabArtifactsResponse } from '@/lib/strategy-lab-artifacts';
import { buildStrategyLabReviewWorkflow } from '@/lib/strategy-lab-review-queue';
import { StrategyLabArtifactsReviewCard } from './strategy-lab-artifacts-review-card';

describe('StrategyLabArtifactsReviewCard', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_KEY;
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
          id: 'quantdinger_verified_readonly_sandbox_proof',
          label: 'QuantDinger verified read-only sandbox proof',
          evidence_kind: 'report_evidence',
          authoritative: false,
          availability: 'available',
          source_path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/status.json',
          source_report_path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/status.json',
          preserved_commit: 'DATA_MISSING',
          preserved_subject: 'DATA_MISSING',
          historical_status: 'verified_readonly_sandbox_viability',
          current_runtime_available: false,
          paper_order_placement: false,
          schema_version: 'DATA_MISSING',
          artifact_id: 'DATA_MISSING',
          artifact_type: 'report',
          review_status: 'PENDING_REVIEW',
          result_status: 'REPORT_ONLY',
          canonical_financial_truth: false,
          execution_allowed: false,
          store_writes: false,
          what_it_proves: ['The clean re-probe records VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY.'],
          what_it_does_not_prove: ['It does not prove current sidecar availability.'],
          data_missing: ['current_sidecar_runtime'],
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
      reviewWorkflow: buildStrategyLabReviewWorkflow({
        generatedAt: '2026-05-24T00:00:00.000Z',
        reviewQueue: [
          {
            id: 'runtime_clean_reprobe_proof',
            label: 'Runtime proof packet',
            group: 'runtime_proof_artifacts',
            source_path:
              'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/runtime_proof.json',
            source_label: 'runtime_proof_json',
            provenance_label: 'VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY',
            priority: 'P0',
            sort_key: '030-runtime-proof',
            filter_tags: ['runtime_proof', 'zero_order'],
            review_status: 'PENDING_REVIEW',
            decision_state: 'PENDING_REVIEW',
            evidence_timestamp: '2026-05-25T01:53:38Z',
            source_commit_ref: 'QuantDinger:91dd4e274702552b91036e2c89018622d111faee',
            source_worktree_ref: '/tmp/tenn-quantdinger-clean-reprobe-v1-20260525/QuantDinger',
            what_is_trustworthy: ['Loopback runtime proof exists as offline evidence.'],
            remains_non_live: ['The sandbox was cleaned up and is not currently available.'],
            promotion_blockers: ['current_sidecar_available=false'],
            unresolved_risks: ['temporary sandbox only'],
            data_missing: ['current_sidecar_runtime'],
            availability: 'available',
          },
          {
            id: 'human_review_decision_absent',
            label: 'Human review decision',
            group: 'review_decisions',
            source_path: 'DATA_MISSING',
            source_label: 'review_decision',
            provenance_label: 'PENDING_REVIEW semantics',
            priority: 'P0',
            sort_key: '060-human-review-decision',
            filter_tags: ['review_decision', 'DATA_MISSING'],
            review_status: 'DATA_MISSING',
            decision_state: 'DATA_MISSING',
            evidence_timestamp: 'DATA_MISSING',
            source_commit_ref: 'DATA_MISSING',
            source_worktree_ref: 'DATA_MISSING',
            what_is_trustworthy: ['No human review decision is present.'],
            remains_non_live: ['Absent review decision blocks promotion.'],
            promotion_blockers: ['human_review_decision=DATA_MISSING'],
            unresolved_risks: ['review owner not encoded'],
            data_missing: ['review_owner'],
            availability: 'missing',
          },
        ],
        experimentSessions: [
          {
            session_id: 'stratlab_qd_clean_reprobe_readonly_20260525',
            label: 'QuantDinger clean read-only sandbox re-probe',
            review_status: 'PENDING_REVIEW',
            current_sidecar_available: false,
            execution_allowed: false,
            canonical_financial_truth: false,
            real_transport: false,
            session_status: 'reviewable_offline_evidence',
            source_commit_ref: 'DATA_MISSING',
            source_worktree_ref: '/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1',
            evidence_timestamps: ['2026-05-25T01:53:38Z'],
            runtime_proof_refs: [],
            reprobe_refs: [],
            degraded_state_refs: [],
            cleanup_proof_refs: [],
            revoke_proof_refs: [],
            review_decision_refs: [],
            promotion_blockers: ['current_sidecar_available=false'],
            unresolved_risks: ['temporary sandbox only'],
            data_missing: ['human_review_decision'],
          },
        ],
        exportPackets: [
          {
            id: 'risk_summary_packet',
            label: 'Risk summary packet',
            packet_type: 'risk_summary_packet',
            path: 'reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/risk_summary_packet.json',
            review_status: 'PENDING_REVIEW',
            source_mode: 'repo_artifacts_only',
            current_sidecar_available: false,
            execution_allowed: false,
            canonical_financial_truth: false,
            real_transport: false,
            summary: 'Open blockers and unresolved risks.',
            data_missing: ['review_owner'],
            availability: 'available',
          },
        ],
      }),
    });
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key';
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    render(<StrategyLabArtifactsReviewCard />);

    expect(await screen.findByText('Strategy Lab Artifact Review')).toBeInTheDocument();
    expect(screen.getByText('Repo-only')).toBeInTheDocument();
    expect(screen.getByText('Pending review')).toBeInTheDocument();
    expect(screen.getByText('Compact drilldown for repo-only proof, review queue, experiment envelope, and export packets.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View details/i })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Runtime proof packet')).not.toBeInTheDocument();
    expect(screen.queryByText('Experiment Session')).not.toBeInTheDocument();
    expect(screen.queryByText('Risk summary packet')).not.toBeInTheDocument();
    expect(screen.queryByText('reports/agent_jobs/source_report')).not.toBeInTheDocument();
    expect(screen.queryByText('NO STORE WRITES')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /View details/i }));

    expect(screen.getByRole('button', { name: /Hide details/i })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Backtest artifact fixture')).toBeInTheDocument();
    expect(screen.getByText('QuantDinger verified read-only sandbox proof')).toBeInTheDocument();
    expect(screen.getByText('Phase 2 helper backtest evidence')).toBeInTheDocument();
    expect(screen.getByText('reports/agent_jobs/source_report')).toBeInTheDocument();
    expect(screen.getByText('helper/pre-envelope')).toBeInTheDocument();
    expect(screen.getByText('verified read-only sandbox proof')).toBeInTheDocument();
    expect(screen.getByText('historical smoke proof')).toBeInTheDocument();
    expect(screen.getByText('0ee837f7dc0706f1b0ff6d6c900522f4c2b43090')).toBeInTheDocument();
    expect(screen.getAllByText('offline').length).toBeGreaterThan(0);
    expect(screen.getByText('Review Queue')).toBeInTheDocument();
    expect(screen.getByText('Runtime proof packet')).toBeInTheDocument();
    expect(screen.getByText('Human review decision')).toBeInTheDocument();
    expect(screen.getByText('Experiment Session')).toBeInTheDocument();
    expect(screen.getByText('QuantDinger clean read-only sandbox re-probe')).toBeInTheDocument();
    expect(screen.getByText('Export Packets')).toBeInTheDocument();
    expect(screen.getByText('Risk summary packet')).toBeInTheDocument();
    expect(screen.getByText(/It does not prove live QuantDinger transport/)).toBeInTheDocument();
    expect(screen.getAllByText('DATA_MISSING').length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/strategy-lab/artifacts',
      expect.objectContaining({
        cache: 'no-store',
        headers: expect.objectContaining({ 'X-API-Key': 'operator-key' }),
      }),
    );
  });
});
