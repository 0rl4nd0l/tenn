import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';

import { GET as getStrategyLabArtifactsRoute } from '@/app/api/cockpit/strategy-lab/artifacts/route';
import type { StrategyLabArtifactsResponse } from './strategy-lab-artifacts';
import { readStrategyLabArtifacts } from './strategy-lab-artifacts-server';

describe('Strategy Lab artifacts contract', () => {
  let workspace: string | null = null;

  afterEach(() => {
    delete process.env.COCKPIT_WORKSPACE_ROOT;
    if (workspace) {
      rmSync(workspace, { recursive: true, force: true });
      workspace = null;
    }
  });

  it('reads only explicit repo artifact paths and preserves deny boundaries', () => {
    workspace = mkdtempSync(path.join(os.tmpdir(), 'strategy-lab-artifacts-'));
    const fixturePath = path.join(workspace, 'docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json');
    mkdirSync(path.dirname(fixturePath), { recursive: true });
    writeFileSync(
      fixturePath,
      JSON.stringify({
        schema_version: 'strategy_lab_artifact_v1',
        artifact_id: 'stratlab_backtest_run_fixture',
        artifact_type: 'backtest_run',
        review_status: 'PENDING_REVIEW',
        result_status: 'SUCCEEDED',
        canonical_financial_truth: false,
        execution_allowed: false,
        may_write_db: false,
        may_write_qdrant: false,
        may_write_memory: false,
        may_write_financial_truth: false,
        data_missing: ['benchmark', 'raw_payload_sha256'],
        provenance: {
          source_report_path: 'reports/agent_jobs/source_report',
        },
      }),
    );
    const milestonePath = path.join(
      workspace,
      'reports/agent_jobs/strategy_lab_quantdinger_complete_and_next_phases_v1_20260524/README.md',
    );
    mkdirSync(path.dirname(milestonePath), { recursive: true });
    writeFileSync(milestonePath, '# QuantDinger complete-and-next-phases\n');
    const cleanReprobeStatusPath = path.join(
      workspace,
      'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/status.json',
    );
    mkdirSync(path.dirname(cleanReprobeStatusPath), { recursive: true });
    writeFileSync(cleanReprobeStatusPath, '{"verdict":"VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY"}\n');

    const payload = readStrategyLabArtifacts({
      now: new Date('2026-05-24T02:00:00.000Z'),
      workspaceRoot: workspace,
    });
    const backtest = payload.artifacts.find((artifact) => artifact.id === 'artifact_v1_backtest_fixture');
    const helper = payload.artifacts.find((artifact) => artifact.id === 'phase2_helper_backtest');
    const milestone = payload.artifacts.find(
      (artifact) => artifact.id === 'quantdinger_complete_next_phases_historical_milestone',
    );
    const verified = payload.artifacts.find(
      (artifact) => artifact.id === 'quantdinger_verified_readonly_sandbox_proof',
    );
    const smoke = payload.artifacts.find((artifact) => artifact.id === 'quantdinger_readonly_sidecar_smoke_proof');

    expect(payload.generated_at).toBe('2026-05-24T02:00:00.000Z');
    expect(payload.source_mode).toBe('repo_artifacts_only');
    expect(payload.boundary_flags).toMatchObject({
      read_only: true,
      live_trading: false,
      paper_trading: false,
      real_transport: false,
      store_writes: false,
      canonical_financial_truth: false,
      production_data_access: false,
    });
    expect(backtest).toMatchObject({
      availability: 'available',
      schema_version: 'strategy_lab_artifact_v1',
      artifact_type: 'backtest_run',
      review_status: 'PENDING_REVIEW',
      canonical_financial_truth: false,
      execution_allowed: false,
      store_writes: false,
      authoritative: true,
    });
    expect(backtest?.data_missing).toContain('benchmark');
    expect(helper).toMatchObject({
      availability: 'missing',
      authoritative: false,
      evidence_kind: 'helper_pre_envelope',
    });
    expect(milestone).toMatchObject({
      availability: 'available',
      historical_status: 'historical_partial_milestone',
      preserved_commit: '72c6d95c70d5b8f6e4ab816967dacc14692941ef',
      current_runtime_available: false,
      paper_order_placement: false,
    });
    expect(verified).toMatchObject({
      availability: 'available',
      historical_status: 'verified_readonly_sandbox_viability',
      current_runtime_available: false,
      paper_order_placement: false,
    });
    expect(verified?.what_it_proves.join(' ')).toContain('VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY');
    expect(verified?.what_it_does_not_prove.join(' ')).toContain('current sidecar availability');
    expect(smoke).toMatchObject({
      availability: 'missing',
      historical_status: 'historical_smoke_proof',
      preserved_commit: '0ee837f7dc0706f1b0ff6d6c900522f4c2b43090',
      current_runtime_available: false,
      paper_order_placement: false,
    });
    expect(smoke?.data_missing).toContain('report_file');
  });

  it('serves the read-only artifact route with no-store caching', async () => {
    workspace = mkdtempSync(path.join(os.tmpdir(), 'strategy-lab-artifacts-route-'));
    const reportPath = path.join(
      workspace,
      'reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/README.md',
    );
    mkdirSync(path.dirname(reportPath), { recursive: true });
    writeFileSync(reportPath, '# Strategy Lab Phase 2\n');
    process.env.COCKPIT_WORKSPACE_ROOT = workspace;

    const response = await getStrategyLabArtifactsRoute();
    const payload = (await response.json()) as StrategyLabArtifactsResponse;

    expect(response.status).toBe(200);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(payload.artifact_review_route).toBe('/api/cockpit/strategy-lab/artifacts');
    expect(payload.artifacts.find((artifact) => artifact.id === 'phase2_schema_report')?.availability).toBe(
      'available',
    );
    expect(payload.artifacts.find((artifact) => artifact.id === 'quantdinger_readonly_sidecar_smoke_proof')).toMatchObject({
      historical_status: 'historical_smoke_proof',
      current_runtime_available: false,
      paper_order_placement: false,
    });
    expect(payload.boundary_flags.store_writes).toBe(false);
  });
});
