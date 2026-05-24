export type StrategyLabAvailability = 'available' | 'missing';

export type StrategyLabArtifactKind =
  | 'schema'
  | 'artifact_fixture'
  | 'mock_transport'
  | 'test'
  | 'report';

export interface StrategyLabBaselineRef {
  id: string;
  label: string;
  kind: StrategyLabArtifactKind;
  path: string;
  summary: string;
}

export interface StrategyLabArtifactRef extends StrategyLabBaselineRef {
  availability: StrategyLabAvailability;
}

export interface StrategyLabCapabilityStatus {
  id: string;
  label: string;
  state: 'present_offline' | 'absent' | 'forbidden' | 'data_missing';
  summary: string;
}

export interface StrategyLabQuantDingerStatus {
  review_status: 'PENDING_REVIEW';
  read_only: true;
  real_transport: 'not_integrated';
  current_sidecar_available: false;
  live_trading: false;
  paper_order_placement: false;
  canonical_financial_truth: false;
  store_writes: false;
  last_readonly_sidecar_smoke: 'SMOKE_PASSED';
  last_readonly_sidecar_smoke_review_status: 'PENDING_REVIEW';
  last_readonly_sidecar_smoke_commit: string;
  last_readonly_sidecar_smoke_report_path: string;
  last_readonly_sidecar_smoke_report_available: false;
  sidecar_runtime_state: 'stopped_after_cleanup';
  data_missing: string[];
}

export interface StrategyLabStatusResponse {
  ok: true;
  schema_version: 'cockpit_strategy_lab_status_v1';
  generated_at: string;
  overall_state: 'pending_review_read_only';
  cockpit_ui_entrypoint: 'home_status_and_artifact_review_cards';
  status_route: '/api/cockpit/strategy-lab/status';
  artifact_review_route: '/api/cockpit/strategy-lab/artifacts';
  headline: string;
  quantdinger_status: StrategyLabQuantDingerStatus;
  artifact_refs: StrategyLabArtifactRef[];
  capability_status: StrategyLabCapabilityStatus[];
  boundary_flags: {
    pending_review: true;
    read_only: true;
    real_transport: false;
    live_trading: false;
    paper_trading: false;
    canonical_financial_truth: false;
    store_writes: false;
    production_data_access: false;
  };
  data_missing: string[];
  next_safe_actions: string[];
}

export const QUANTDINGER_HISTORICAL_STATUS: StrategyLabQuantDingerStatus = {
  review_status: 'PENDING_REVIEW',
  read_only: true,
  real_transport: 'not_integrated',
  current_sidecar_available: false,
  live_trading: false,
  paper_order_placement: false,
  canonical_financial_truth: false,
  store_writes: false,
  last_readonly_sidecar_smoke: 'SMOKE_PASSED',
  last_readonly_sidecar_smoke_review_status: 'PENDING_REVIEW',
  last_readonly_sidecar_smoke_commit: '0ee837f7dc0706f1b0ff6d6c900522f4c2b43090',
  last_readonly_sidecar_smoke_report_path:
    'reports/agent_jobs/strategy_lab_quantdinger_readonly_sidecar_smoke_exec_v1_20260524/status.json',
  last_readonly_sidecar_smoke_report_available: false,
  sidecar_runtime_state: 'stopped_after_cleanup',
  data_missing: [
    'The read-only smoke report bundle is preserved at commit 0ee837f7 but is not checked out as files in this worktree.',
    'No current QuantDinger sidecar runtime was probed under this status route.',
    'No current QuantDinger transport is integrated with Cockpit.',
  ],
};

export const STRATEGY_LAB_BASELINE_REFS: StrategyLabBaselineRef[] = [
  {
    id: 'artifact_schema_doc',
    label: 'Artifact schema',
    kind: 'schema',
    path: 'docs/strategy_lab/artifact_schema_v1.md',
    summary: 'Authoritative pending-review Strategy Lab artifact boundary.',
  },
  {
    id: 'artifact_schema_json',
    label: 'Artifact schema JSON',
    kind: 'schema',
    path: 'docs/strategy_lab/artifact_schema_v1.schema.json',
    summary: 'Machine-readable envelope shape for offline validation.',
  },
  {
    id: 'backtest_fixture',
    label: 'Backtest artifact fixture',
    kind: 'artifact_fixture',
    path: 'docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json',
    summary: 'Saved QuantDinger-shaped backtest result mapped to PENDING_REVIEW.',
  },
  {
    id: 'regime_fixture',
    label: 'Regime artifact fixture',
    kind: 'artifact_fixture',
    path: 'docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json',
    summary: 'Saved regime-detect result mapped to PENDING_REVIEW.',
  },
  {
    id: 'mock_transport_contract',
    label: 'Offline mock transport contract',
    kind: 'mock_transport',
    path: 'docs/strategy_lab/mock_transport/offline_mock_transport_contract_v1.md',
    summary: 'Design and test layer only; no real QuantDinger transport.',
  },
  {
    id: 'mock_capabilities_fixture',
    label: 'Mock capabilities response',
    kind: 'mock_transport',
    path: 'docs/strategy_lab/mock_transport_fixtures/valid_capabilities_transport_response_v1.json',
    summary: 'Local fixture proving mock-only capabilities shape.',
  },
  {
    id: 'mock_adapter_tests',
    label: 'Mock adapter tests',
    kind: 'test',
    path: 'tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py',
    summary: 'Offline policy and artifact invariant coverage.',
  },
  {
    id: 'mock_transport_tests',
    label: 'Mock transport tests',
    kind: 'test',
    path: 'tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py',
    summary: 'Offline mock transport lifecycle and blocked-surface coverage.',
  },
  {
    id: 'phase3g_mergeback_report',
    label: 'Phase 3G mergeback report',
    kind: 'report',
    path: 'reports/agent_jobs/strategy_lab_phase3g_mergeback_v1_20260524/README.md',
    summary: 'Current baseline preservation report for Strategy Lab evidence.',
  },
];

export function buildStrategyLabStatusResponse({
  generatedAt,
  artifactRefs,
}: {
  generatedAt: string;
  artifactRefs: StrategyLabArtifactRef[];
}): StrategyLabStatusResponse {
  return {
    ok: true,
    schema_version: 'cockpit_strategy_lab_status_v1',
    generated_at: generatedAt,
    overall_state: 'pending_review_read_only',
    cockpit_ui_entrypoint: 'home_status_and_artifact_review_cards',
    status_route: '/api/cockpit/strategy-lab/status',
    artifact_review_route: '/api/cockpit/strategy-lab/artifacts',
    headline:
      'Strategy Lab / QuantDinger is visible as read-only pending-review evidence, not live trading functionality.',
    quantdinger_status: QUANTDINGER_HISTORICAL_STATUS,
    artifact_refs: artifactRefs,
    capability_status: [
      {
        id: 'cockpit_visibility',
        label: 'Cockpit visibility',
        state: 'present_offline',
        summary: 'Home shows a read-only status card backed by repository artifact presence.',
      },
      {
        id: 'historical_readonly_smoke',
        label: 'Historical read-only smoke',
        state: 'present_offline',
        summary: 'Commit 0ee837f7 preserves a past loopback read-only smoke proof with PENDING_REVIEW status.',
      },
      {
        id: 'current_sidecar',
        label: 'Current sidecar runtime',
        state: 'absent',
        summary: 'The smoke sidecar was cleaned up; current_sidecar_available remains false.',
      },
      {
        id: 'artifact_schema',
        label: 'Artifact schema',
        state: 'present_offline',
        summary: 'Existing Strategy Lab artifact contracts remain the boundary.',
      },
      {
        id: 'mock_transport',
        label: 'Mock transport',
        state: 'present_offline',
        summary: 'Only offline mock fixtures and tests are present.',
      },
      {
        id: 'real_transport',
        label: 'Real sidecar transport',
        state: 'absent',
        summary: 'No real QuantDinger adapter, client, MCP/API call path, auth, retry, or timeout behavior is wired.',
      },
      {
        id: 'trading',
        label: 'Trading and execution',
        state: 'forbidden',
        summary: 'Broker, paper, live, order, bot, and portfolio mutation surfaces are not enabled.',
      },
      {
        id: 'canonical_truth',
        label: 'Canonical financial truth',
        state: 'forbidden',
        summary: 'Sidecar artifacts are external context only and cannot become Tenn financial truth here.',
      },
    ],
    boundary_flags: {
      pending_review: true,
      read_only: true,
      real_transport: false,
      live_trading: false,
      paper_trading: false,
      canonical_financial_truth: false,
      store_writes: false,
      production_data_access: false,
    },
    data_missing: [
      'No real QuantDinger sidecar capability, auth, network transport, retry, timeout, or unavailable behavior has been confirmed.',
      'No artifact persistence store, review queue, or promotion workflow is implemented in Cockpit.',
      'No evidence-backed parameter_sweep, factor_test, broad risk_report, or portfolio_experiment surface is live.',
    ],
    next_safe_actions: [
      'Review the pending Strategy Lab artifact fixtures and Phase 3G preservation report.',
      'Use the repo-only artifact review route for existing fixtures and reports.',
      'Keep any future real sidecar smoke isolated, explicitly approved, and non-trading.',
    ],
  };
}
