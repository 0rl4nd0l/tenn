import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';

import { STRATEGY_LAB_REVIEW_QUEUE_SOURCES, buildStrategyLabReviewWorkflow } from './strategy-lab-review-queue';
import { readStrategyLabReviewWorkflow } from './strategy-lab-review-queue-server';

describe('Strategy Lab review workflow', () => {
  let workspace: string | null = null;

  afterEach(() => {
    if (workspace) {
      rmSync(workspace, { recursive: true, force: true });
      workspace = null;
    }
  });

  it('keeps review queue semantics repo-backed, pending-review, and non-promoting', () => {
    const queue = STRATEGY_LAB_REVIEW_QUEUE_SOURCES.map((source) => ({
      ...source,
      availability: source.source_path === 'DATA_MISSING' ? ('missing' as const) : ('available' as const),
    }));
    const workflow = buildStrategyLabReviewWorkflow({
      generatedAt: '2026-05-25T04:48:03.000Z',
      reviewQueue: queue,
      experimentSessions: [],
      exportPackets: [],
    });

    expect(workflow.schema_version).toBe('cockpit_strategy_lab_review_workflow_v1');
    expect(workflow.source_mode).toBe('repo_artifacts_only');
    expect(workflow.review_status).toBe('PENDING_REVIEW');
    expect(workflow.current_sidecar_available).toBe(false);
    expect(workflow.execution_allowed).toBe(false);
    expect(workflow.canonical_financial_truth).toBe(false);
    expect(workflow.real_transport).toBe(false);
    expect(workflow.sort_options).toContain('priority_then_sort_key');
    expect(workflow.filter_facets).toContain('group');
    expect(workflow.group_summaries.find((group) => group.group === 'runtime_proof_artifacts')).toMatchObject({
      label: 'Runtime proof artifacts',
      total: 1,
      available: 1,
      pending_review: 1,
    });
    expect(workflow.review_queue[0].priority).toBe('P0');
    expect(workflow.review_queue.find((item) => item.id === 'human_review_decision_absent')).toMatchObject({
      review_status: 'DATA_MISSING',
      availability: 'missing',
      decision_state: 'DATA_MISSING',
    });
    expect(workflow.review_queue.find((item) => item.id === 'promotion_gate_bundle')).toMatchObject({
      review_status: 'BLOCKED',
      decision_state: 'PROMOTION_BLOCKED',
    });
  });

  it('resolves experiment session refs and packet availability without runtime probes', () => {
    const workspaceRoot = mkdtempSync(path.join(os.tmpdir(), 'strategy-lab-review-workflow-'));
    workspace = workspaceRoot;
    const statusPath = writeWorkspaceFile(
      workspaceRoot,
      'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/status.json',
      '{"verdict":"VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY"}\n',
    );
    writeWorkspaceFile(
      workspaceRoot,
      'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/runtime_proof.json',
      '{"schema_version":1}\n',
    );
    writeWorkspaceFile(
      workspaceRoot,
      'reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/risk_summary_packet.json',
      '{"schema_version":1}\n',
    );

    const workflow = readStrategyLabReviewWorkflow({
      generatedAt: '2026-05-25T04:49:00.000Z',
      workspaceRoot,
      artifacts: [
        {
          id: 'quantdinger_verified_readonly_sandbox_proof',
          label: 'QuantDinger verified read-only sandbox proof',
          evidence_kind: 'report_evidence',
          authoritative: false,
          availability: 'available',
          source_path: statusPath.relativePath,
          source_report_path: statusPath.relativePath,
          preserved_commit: 'DATA_MISSING',
          preserved_subject: 'DATA_MISSING',
          historical_status: 'verified_readonly_sandbox_viability',
          current_runtime_available: false,
          paper_order_placement: false,
          schema_version: 'DATA_MISSING',
          artifact_id: 'DATA_MISSING',
          artifact_type: 'report',
          review_status: 'PENDING_REVIEW',
          result_status: 'VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY',
          canonical_financial_truth: false,
          execution_allowed: false,
          store_writes: false,
          what_it_proves: ['verified read-only proof exists'],
          what_it_does_not_prove: ['current sidecar availability'],
          data_missing: ['current_sidecar_runtime'],
        },
      ],
    });

    const session = workflow.experiment_sessions[0];
    expect(session.session_status).toBe('reviewable_offline_evidence');
    expect(session.current_sidecar_available).toBe(false);
    expect(session.execution_allowed).toBe(false);
    expect(session.canonical_financial_truth).toBe(false);
    expect(session.real_transport).toBe(false);
    expect(session.runtime_proof_refs.find((ref) => ref.id === 'runtime_proof')?.availability).toBe('available');
    expect(session.cleanup_proof_refs.find((ref) => ref.id === 'cleanup_proof')?.availability).toBe('missing');
    expect(workflow.export_packets.find((packet) => packet.id === 'risk_summary_packet')?.availability).toBe(
      'available',
    );
    expect(workflow.export_packets.find((packet) => packet.id === 'experiment_review_packet')?.availability).toBe(
      'missing',
    );
  });
});

function writeWorkspaceFile(workspace: string, relativePath: string, contents: string) {
  const targetPath = path.join(workspace, relativePath);
  mkdirSync(path.dirname(targetPath), { recursive: true });
  writeFileSync(targetPath, contents);
  return { targetPath, relativePath };
}
