import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';

import { GET as getStrategyLabStatusRoute } from '@/app/api/cockpit/strategy-lab/status/route';
import {
  STRATEGY_LAB_BASELINE_REFS,
  buildStrategyLabStatusResponse,
  type StrategyLabStatusResponse,
} from './strategy-lab-status';
import { readStrategyLabStatus } from './strategy-lab-status-server';

describe('Strategy Lab status contract', () => {
  let workspace: string | null = null;

  afterEach(() => {
    delete process.env.COCKPIT_WORKSPACE_ROOT;
    if (workspace) {
      rmSync(workspace, { recursive: true, force: true });
      workspace = null;
    }
  });

  it('keeps QuantDinger visible only as pending-review read-only evidence', () => {
    const payload = buildStrategyLabStatusResponse({
      generatedAt: '2026-05-24T00:00:00.000Z',
      artifactRefs: STRATEGY_LAB_BASELINE_REFS.map((ref) => ({
        ...ref,
        availability: 'available',
      })),
    });

    expect(payload.overall_state).toBe('pending_review_read_only');
    expect(payload.boundary_flags).toMatchObject({
      pending_review: true,
      read_only: true,
      real_transport: false,
      live_trading: false,
      paper_trading: false,
      canonical_financial_truth: false,
      store_writes: false,
      production_data_access: false,
    });
    expect(payload.capability_status.find((capability) => capability.id === 'real_transport')?.state).toBe('absent');
    expect(payload.capability_status.find((capability) => capability.id === 'trading')?.state).toBe('forbidden');
    expect(payload.data_missing.join(' ')).toContain('No real QuantDinger sidecar capability');
  });

  it('reports artifact availability from the workspace without writing stores', () => {
    workspace = mkdtempSync(path.join(os.tmpdir(), 'strategy-lab-status-'));
    const schemaPath = path.join(workspace, 'docs/strategy_lab/artifact_schema_v1.md');
    mkdirSync(path.dirname(schemaPath), { recursive: true });
    writeFileSync(schemaPath, '# Strategy Lab Artifact Schema\n');

    const payload = readStrategyLabStatus({
      now: new Date('2026-05-24T01:00:00.000Z'),
      workspaceRoot: workspace,
    });

    expect(payload.generated_at).toBe('2026-05-24T01:00:00.000Z');
    expect(payload.artifact_refs.find((ref) => ref.id === 'artifact_schema_doc')?.availability).toBe('available');
    expect(payload.artifact_refs.find((ref) => ref.id === 'backtest_fixture')?.availability).toBe('missing');
    expect(payload.boundary_flags.store_writes).toBe(false);
  });

  it('serves the read-only status route with no-store caching', async () => {
    workspace = mkdtempSync(path.join(os.tmpdir(), 'strategy-lab-route-'));
    const reportPath = path.join(
      workspace,
      'reports/agent_jobs/strategy_lab_phase3g_mergeback_v1_20260524/README.md',
    );
    mkdirSync(path.dirname(reportPath), { recursive: true });
    writeFileSync(reportPath, '# Strategy Lab Phase 3G Mergeback\n');
    process.env.COCKPIT_WORKSPACE_ROOT = workspace;

    const response = await getStrategyLabStatusRoute();
    const payload = (await response.json()) as StrategyLabStatusResponse;

    expect(response.status).toBe(200);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(payload.status_route).toBe('/api/cockpit/strategy-lab/status');
    expect(payload.artifact_review_route).toBe('/api/cockpit/strategy-lab/artifacts');
    expect(payload.artifact_refs.find((ref) => ref.id === 'phase3g_mergeback_report')?.availability).toBe('available');
    expect(payload.boundary_flags.live_trading).toBe(false);
  });
});
