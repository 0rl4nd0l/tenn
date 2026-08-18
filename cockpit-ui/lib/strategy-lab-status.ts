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

export interface StrategyLabEvidenceArtifactBaselineRef {
  id: string;
  label: string;
  path: string;
  summary: string;
}

export interface StrategyLabEvidenceArtifactRef extends StrategyLabEvidenceArtifactBaselineRef {
  availability: StrategyLabAvailability;
}

export interface StrategyLabCapabilityStatus {
  id: string;
  label: string;
  state: 'present_offline' | 'absent' | 'forbidden' | 'data_missing';
  summary: string;
}

export interface StrategyLabVerifiedReadonlySandboxProof {
  verdict: 'VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY';
  review_status: 'PENDING_REVIEW';
  current_sidecar_available: false;
  sidecar_runtime_state: 'stopped_after_cleanup';
  report_path: string;
  report_available: StrategyLabAvailability;
  evidence_artifacts: StrategyLabEvidenceArtifactRef[];
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
  verified_readonly_sandbox: StrategyLabVerifiedReadonlySandboxProof;
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

export interface StrategyLabHomeSummary {
  status: 'Read-only sandbox proof verified';
  currentRuntime: 'Offline';
  reviewState: 'Pending review';
  tradingExecution: 'Disabled';
  valueSummary: string;
  blockerSummary: string;
  detailRoute: StrategyLabStatusResponse['artifact_review_route'];
  statusRoute: StrategyLabStatusResponse['status_route'];
  availableArtifactCount: number;
  totalArtifactCount: number;
  availableEvidenceCount: number;
  totalEvidenceCount: number;
}

export const VERIFIED_READONLY_SANDBOX_REPORT_PATH =
  'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/README.md';

export const VERIFIED_READONLY_SANDBOX_EVIDENCE_REFS: StrategyLabEvidenceArtifactBaselineRef[] = [
  {
    id: 'clean_reprobe_readme',
    label: 'Clean re-probe README',
    path: VERIFIED_READONLY_SANDBOX_REPORT_PATH,
    summary: 'Human-readable verdict and evidence index for the clean QuantDinger re-probe.',
  },
  {
    id: 'clean_reprobe_status',
    label: 'Clean re-probe status',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/status.json',
    summary: 'Machine-readable verdict, current_sidecar_available=false, and no-mutation summary.',
  },
  {
    id: 'clean_reprobe_runtime_proof',
    label: 'Runtime proof',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/runtime_proof.json',
    summary: 'Loopback sandbox runtime, read/backtest, regime, denial, revoke, and zero-order evidence.',
  },
  {
    id: 'clean_reprobe_cleanup_proof',
    label: 'Cleanup proof',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/cleanup_proof.json',
    summary: 'Proof that containers, volumes, network, image, listeners, and temp sandbox were removed.',
  },
  {
    id: 'clean_reprobe_no_mutation_attestation',
    label: 'No-mutation attestation',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/no_mutation_attestation.json',
    summary: 'Attestation that Tenn stores, Strategy Lab status, and current availability were not mutated.',
  },
  {
    id: 'clean_reprobe_validation',
    label: 'Validation log',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/validation.json',
    summary: 'Validation command outcomes for the clean re-probe evidence packet.',
  },
  {
    id: 'clean_reprobe_backtest_request',
    label: 'Backtest request',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/backtest_request.json',
    summary: 'Sanitized backtest request payload.',
  },
  {
    id: 'clean_reprobe_backtest_final_response',
    label: 'Backtest final response',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/backtest_final_response.json',
    summary: 'Sanitized final backtest response body.',
  },
  {
    id: 'clean_reprobe_regime_request',
    label: 'Regime request',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/regime_request.json',
    summary: 'Sanitized regime-detect request payload.',
  },
  {
    id: 'clean_reprobe_regime_response',
    label: 'Regime response',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/regime_response.json',
    summary: 'Sanitized regime-detect response body.',
  },
  {
    id: 'clean_reprobe_denial_responses',
    label: 'Denied write/trade probes',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/denial_responses.json',
    summary: 'Denied W/T scope and order probes.',
  },
  {
    id: 'clean_reprobe_zero_order_proof',
    label: 'Zero-order proof',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/zero_order_proof.json',
    summary: 'API and DB order counts before and after the read/backtest probe.',
  },
  {
    id: 'clean_reprobe_revoke_response',
    label: 'Revoke response',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/revoke_response.json',
    summary: 'Token revoke response.',
  },
  {
    id: 'clean_reprobe_post_revoke_whoami',
    label: 'Post-revoke whoami',
    path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/post_revoke_whoami_response.json',
    summary: 'Post-revoke request proving the token no longer authenticated.',
  },
];

function missingEvidenceRefs(): StrategyLabEvidenceArtifactRef[] {
  return VERIFIED_READONLY_SANDBOX_EVIDENCE_REFS.map((ref) => ({
    ...ref,
    availability: 'missing',
  }));
}

function buildVerifiedReadonlySandboxProof(
  evidenceArtifacts: StrategyLabEvidenceArtifactRef[] = missingEvidenceRefs(),
): StrategyLabVerifiedReadonlySandboxProof {
  const reportAvailable =
    evidenceArtifacts.find((artifact) => artifact.path === VERIFIED_READONLY_SANDBOX_REPORT_PATH)?.availability ??
    'missing';

  return {
    verdict: 'VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY',
    review_status: 'PENDING_REVIEW',
    current_sidecar_available: false,
    sidecar_runtime_state: 'stopped_after_cleanup',
    report_path: VERIFIED_READONLY_SANDBOX_REPORT_PATH,
    report_available: reportAvailable,
    evidence_artifacts: evidenceArtifacts,
  };
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
  verified_readonly_sandbox: buildVerifiedReadonlySandboxProof(),
  data_missing: [
    'The read-only smoke report bundle is preserved at commit 0ee837f7 but is not checked out as files in this worktree.',
    'The status route reads persisted repo artifacts only and does not probe current QuantDinger runtime.',
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
    id: 'verified_readonly_sandbox_report',
    label: 'Verified read-only sandbox proof',
    kind: 'report',
    path: VERIFIED_READONLY_SANDBOX_REPORT_PATH,
    summary: 'Clean re-probe evidence for verified read-only sandbox viability; current_sidecar_available remains false.',
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
  verifiedReadonlySandboxEvidenceRefs,
}: {
  generatedAt: string;
  artifactRefs: StrategyLabArtifactRef[];
  verifiedReadonlySandboxEvidenceRefs?: StrategyLabEvidenceArtifactRef[];
}): StrategyLabStatusResponse {
  const verifiedReadonlySandbox = buildVerifiedReadonlySandboxProof(verifiedReadonlySandboxEvidenceRefs);

  return {
    ok: true,
    schema_version: 'cockpit_strategy_lab_status_v1',
    generated_at: generatedAt,
    overall_state: 'pending_review_read_only',
    cockpit_ui_entrypoint: 'home_status_and_artifact_review_cards',
    status_route: '/api/cockpit/strategy-lab/status',
    artifact_review_route: '/api/cockpit/strategy-lab/artifacts',
    headline:
      'Verified read-only sandbox proof available; Strategy Lab / QuantDinger remains pending-review, offline, non-trading evidence.',
    quantdinger_status: {
      ...QUANTDINGER_HISTORICAL_STATUS,
      verified_readonly_sandbox: verifiedReadonlySandbox,
    },
    artifact_refs: artifactRefs,
    capability_status: [
      {
        id: 'cockpit_visibility',
        label: 'Cockpit visibility',
        state: 'present_offline',
        summary: 'Home shows a read-only status card backed by repository artifact presence.',
      },
      {
        id: 'verified_readonly_sandbox',
        label: 'Verified read-only sandbox proof',
        state: 'present_offline',
        summary:
          'Clean re-probe evidence records VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY; current_sidecar_available remains false.',
      },
      {
        id: 'review_queue',
        label: 'Review queue',
        state: 'present_offline',
        summary:
          'The artifact route exposes repo-backed PENDING_REVIEW queue, experiment session, and export packet semantics.',
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
      'No current QuantDinger sidecar capability, auth, network transport, retry, timeout, or unavailable behavior is confirmed by this status route.',
      'Review queue and export packets are repo-backed artifacts only; no artifact persistence store or promotion workflow is implemented.',
      'No evidence-backed parameter_sweep, factor_test, broad risk_report, or portfolio_experiment surface is live.',
    ],
    next_safe_actions: [
      'Review the clean re-probe evidence artifacts and keep results PENDING_REVIEW.',
      'Use the repo-only artifact review route for existing fixtures and reports.',
      'Keep any future real sidecar smoke isolated, explicitly approved, and non-trading.',
    ],
  };
}

export function buildStrategyLabHomeSummary(payload: StrategyLabStatusResponse): StrategyLabHomeSummary {
  const availableArtifactCount = payload.artifact_refs.filter((artifact) => artifact.availability === 'available').length;
  const evidenceArtifacts = payload.quantdinger_status.verified_readonly_sandbox.evidence_artifacts;
  const availableEvidenceCount = evidenceArtifacts.filter((artifact) => artifact.availability === 'available').length;
  const blocker =
    payload.data_missing[0] ??
    payload.quantdinger_status.data_missing[0] ??
    'DATA_MISSING: current sidecar transport and review decision remain unresolved.';

  return {
    status: 'Read-only sandbox proof verified',
    currentRuntime: 'Offline',
    reviewState: 'Pending review',
    tradingExecution: 'Disabled',
    valueSummary: 'Repo-backed proof exists for read-only sandbox behavior; QD is not live or executable.',
    blockerSummary: `DATA_MISSING: ${blocker.replace(/^DATA_MISSING:\s*/i, '')}`,
    detailRoute: payload.artifact_review_route,
    statusRoute: payload.status_route,
    availableArtifactCount,
    totalArtifactCount: payload.artifact_refs.length,
    availableEvidenceCount,
    totalEvidenceCount: evidenceArtifacts.length,
  };
}
