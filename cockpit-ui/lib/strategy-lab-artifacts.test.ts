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

    const payload = readStrategyLabArtifacts({
      now: new Date('2026-05-24T02:00:00.000Z'),
      workspaceRoot: workspace,
    });
    const backtest = payload.artifacts.find((artifact) => artifact.id === 'artifact_v1_backtest_fixture');
    const helper = payload.artifacts.find((artifact) => artifact.id === 'phase2_helper_backtest');

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
    expect(payload.boundary_flags.store_writes).toBe(false);
  });
});
