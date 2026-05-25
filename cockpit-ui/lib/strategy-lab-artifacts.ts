export type StrategyLabReviewEvidenceKind =
  | 'strategy_lab_artifact_v1'
  | 'helper_pre_envelope'
  | 'report_evidence';

export type StrategyLabReviewAvailability = 'available' | 'missing' | 'invalid_json';

export type StrategyLabHistoricalEvidenceStatus =
  | 'historical_partial_milestone'
  | 'historical_smoke_proof'
  | 'verified_readonly_sandbox_viability'
  | 'DATA_MISSING';

export interface StrategyLabReviewSource {
  id: string;
  label: string;
  evidence_kind: StrategyLabReviewEvidenceKind;
  authoritative: boolean;
  source_path: string;
  preserved_commit?: string;
  preserved_subject?: string;
  historical_status?: StrategyLabHistoricalEvidenceStatus;
  current_runtime_available?: false;
  paper_order_placement?: false;
  review_status?: 'PENDING_REVIEW';
  result_status?: string;
  canonical_financial_truth?: false;
  execution_allowed?: false;
  store_writes?: false;
  what_it_proves: string[];
  what_it_does_not_prove: string[];
  data_missing: string[];
}

export interface StrategyLabReviewArtifact {
  id: string;
  label: string;
  evidence_kind: StrategyLabReviewEvidenceKind;
  authoritative: boolean;
  availability: StrategyLabReviewAvailability;
  source_path: string;
  source_report_path: string;
  preserved_commit: string;
  preserved_subject: string;
  historical_status: StrategyLabHistoricalEvidenceStatus;
  current_runtime_available: false | 'DATA_MISSING';
  paper_order_placement: false | 'DATA_MISSING';
  schema_version: string;
  artifact_id: string;
  artifact_type: string;
  review_status: string;
  result_status: string;
  canonical_financial_truth: boolean | 'DATA_MISSING';
  execution_allowed: boolean | 'DATA_MISSING';
  store_writes: boolean | 'DATA_MISSING';
  what_it_proves: string[];
  what_it_does_not_prove: string[];
  data_missing: string[];
}

export interface StrategyLabArtifactsResponse {
  ok: true;
  schema_version: 'cockpit_strategy_lab_artifacts_v1';
  generated_at: string;
  artifact_review_route: '/api/cockpit/strategy-lab/artifacts';
  source_mode: 'repo_artifacts_only';
  artifacts: StrategyLabReviewArtifact[];
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
}

export const STRATEGY_LAB_REVIEW_SOURCES: StrategyLabReviewSource[] = [
  {
    id: 'artifact_v1_backtest_fixture',
    label: 'Backtest artifact fixture',
    evidence_kind: 'strategy_lab_artifact_v1',
    authoritative: true,
    source_path: 'docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json',
    what_it_proves: [
      'A parseable strategy_lab_artifact_v1 backtest_run fixture exists in the repo.',
      'The fixture is PENDING_REVIEW, read-only, non-canonical, and execution-disabled.',
    ],
    what_it_does_not_prove: [
      'It does not prove live QuantDinger transport is available.',
      'It does not prove investment correctness, canonical financial truth, paper trading, or live trading.',
    ],
    data_missing: ['live_sidecar_transport', 'investment_correctness', 'runtime_artifact_store'],
  },
  {
    id: 'artifact_v1_regime_fixture',
    label: 'Regime artifact fixture',
    evidence_kind: 'strategy_lab_artifact_v1',
    authoritative: true,
    source_path: 'docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json',
    what_it_proves: [
      'A parseable strategy_lab_artifact_v1 regime_breakdown fixture exists in the repo.',
      'The fixture is PENDING_REVIEW, read-only, non-canonical, and execution-disabled.',
    ],
    what_it_does_not_prove: [
      'It does not prove a current regime detector is callable from Cockpit.',
      'It does not prove production-data access, canonical financial truth, or trading readiness.',
    ],
    data_missing: ['current_sidecar_capability', 'explicit_provider_field', 'runtime_artifact_store'],
  },
  {
    id: 'artifact_v1_strategy_idea_fixture',
    label: 'Strategy idea fixture',
    evidence_kind: 'strategy_lab_artifact_v1',
    authoritative: true,
    source_path: 'docs/strategy_lab/artifact_fixtures/valid_strategy_idea_v1.json',
    what_it_proves: [
      'A Tenn-owned strategy_idea fixture exists for the Strategy Lab artifact envelope.',
      'The fixture keeps review status pending and does not permit execution or store writes.',
    ],
    what_it_does_not_prove: [
      'It does not prove a QuantDinger run occurred for this idea.',
      'It does not prove a human review queue or promotion workflow exists.',
    ],
    data_missing: ['raw_external_payload', 'human_review_queue', 'promotion_workflow'],
  },
  {
    id: 'phase2_helper_backtest',
    label: 'Phase 2 helper backtest evidence',
    evidence_kind: 'helper_pre_envelope',
    authoritative: false,
    source_path:
      'reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/backtest_run.json',
    what_it_proves: [
      'A Phase 2 normalized sidecar helper artifact exists for a backtest_run sample.',
      'Its stored guardrail flags deny execution, canonical truth, and Tenn store writes.',
    ],
    what_it_does_not_prove: [
      'It is strategy_lab_sidecar_artifact_v1 helper evidence, not the authoritative strategy_lab_artifact_v1 envelope.',
      'It does not prove real transport, current sidecar availability, or investment correctness.',
    ],
    data_missing: ['strategy_lab_artifact_v1_envelope', 'raw_payload_ref', 'runtime_validator'],
  },
  {
    id: 'phase2_helper_regime',
    label: 'Phase 2 helper regime evidence',
    evidence_kind: 'helper_pre_envelope',
    authoritative: false,
    source_path:
      'reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/regime_breakdown.json',
    what_it_proves: [
      'A Phase 2 normalized sidecar helper artifact exists for a regime_breakdown sample.',
      'Its stored guardrail flags deny execution, canonical truth, and Tenn store writes.',
    ],
    what_it_does_not_prove: [
      'It is strategy_lab_sidecar_artifact_v1 helper evidence, not the authoritative strategy_lab_artifact_v1 envelope.',
      'It does not prove a current sidecar regime endpoint is callable from Cockpit.',
    ],
    data_missing: ['strategy_lab_artifact_v1_envelope', 'raw_payload_ref', 'current_endpoint_probe'],
  },
  {
    id: 'phase2_schema_report',
    label: 'Phase 2 artifact schema report',
    evidence_kind: 'report_evidence',
    authoritative: false,
    source_path: 'reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/README.md',
    what_it_proves: [
      'A repo report records the schema-only Phase 2 boundary and validation result.',
      'The report states no runtime, Cockpit, store, credential, paper, or live execution setup was performed.',
    ],
    what_it_does_not_prove: [
      'It is not an artifact envelope.',
      'It does not prove a live review queue, live transport, or canonical truth integration exists.',
    ],
    data_missing: ['artifact_envelope_fields', 'live_sidecar_transport', 'review_queue'],
  },
  {
    id: 'quantdinger_complete_next_phases_historical_milestone',
    label: 'QuantDinger complete-and-next-phases milestone',
    evidence_kind: 'report_evidence',
    authoritative: false,
    source_path: 'reports/agent_jobs/strategy_lab_quantdinger_complete_and_next_phases_v1_20260524/README.md',
    preserved_commit: '72c6d95c70d5b8f6e4ab816967dacc14692941ef',
    preserved_subject: 'milestone(reporting): preserve quantdinger next phases evidence',
    historical_status: 'historical_partial_milestone',
    current_runtime_available: false,
    paper_order_placement: false,
    what_it_proves: [
      'A preserved historical report records QuantDinger complete-and-next-phases decision evidence.',
      'The milestone is useful as partial planning context for Strategy Lab review.',
    ],
    what_it_does_not_prove: [
      'It does not prove current QuantDinger runtime, current sidecar availability, or transport integration.',
      'It must not override the later read-only smoke proof preserved at commit 0ee837f7.',
    ],
    data_missing: ['current_sidecar_runtime', 'current_transport_probe', 'review_owner_decision'],
  },
  {
    id: 'quantdinger_verified_readonly_sandbox_proof',
    label: 'QuantDinger verified read-only sandbox proof',
    evidence_kind: 'report_evidence',
    authoritative: false,
    source_path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/status.json',
    historical_status: 'verified_readonly_sandbox_viability',
    current_runtime_available: false,
    paper_order_placement: false,
    review_status: 'PENDING_REVIEW',
    result_status: 'VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY',
    canonical_financial_truth: false,
    execution_allowed: false,
    store_writes: false,
    what_it_proves: [
      'The clean re-probe records VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY and remains PENDING_REVIEW.',
      'Exact status, runtime, cleanup, no-mutation, zero-order, revoke, and sanitized request/response artifacts are available.',
    ],
    what_it_does_not_prove: [
      'It does not prove current sidecar availability because the sandbox was cleaned up after execution.',
      'It does not enable transport integration, live trading, paper orders, store writes, or canonical financial truth.',
    ],
    data_missing: ['current_sidecar_runtime', 'transport_integration', 'review_owner_decision'],
  },
  {
    id: 'quantdinger_readonly_sidecar_smoke_proof',
    label: 'QuantDinger read-only sidecar smoke proof',
    evidence_kind: 'report_evidence',
    authoritative: false,
    source_path: 'reports/agent_jobs/strategy_lab_quantdinger_readonly_sidecar_smoke_exec_v1_20260524/status.json',
    preserved_commit: '0ee837f7dc0706f1b0ff6d6c900522f4c2b43090',
    preserved_subject: 'milestone(reporting): preserve quantdinger readonly smoke proof',
    historical_status: 'historical_smoke_proof',
    current_runtime_available: false,
    paper_order_placement: false,
    review_status: 'PENDING_REVIEW',
    canonical_financial_truth: false,
    execution_allowed: false,
    store_writes: false,
    what_it_proves: [
      'A later preserved commit records a bounded loopback read-only smoke that passed and remains PENDING_REVIEW.',
      'The smoke evidence supports historical last_readonly_sidecar_smoke=SMOKE_PASSED only.',
    ],
    what_it_does_not_prove: [
      'It does not prove current sidecar availability because the smoke runtime was cleaned up after execution.',
      'It does not enable live trading, paper order placement, or canonical financial truth writes.',
    ],
    data_missing: ['report_file_in_current_worktree', 'current_sidecar_runtime', 'current_transport_probe'],
  },
];

export function buildStrategyLabArtifactsResponse({
  generatedAt,
  artifacts,
}: {
  generatedAt: string;
  artifacts: StrategyLabReviewArtifact[];
}): StrategyLabArtifactsResponse {
  return {
    ok: true,
    schema_version: 'cockpit_strategy_lab_artifacts_v1',
    generated_at: generatedAt,
    artifact_review_route: '/api/cockpit/strategy-lab/artifacts',
    source_mode: 'repo_artifacts_only',
    artifacts,
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
      'No real QuantDinger sidecar transport, auth, retry, timeout, or unavailable behavior is confirmed.',
      'The verified read-only sandbox proof does not prove a current online sidecar or real Cockpit transport.',
      'No Cockpit artifact persistence store, review decision queue, or promotion workflow is implemented.',
      'No DB, Qdrant, memory, news, canonical financial truth, paper trading, or live trading write path is used.',
    ],
  };
}
