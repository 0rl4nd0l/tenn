export type StrategyLabReviewEvidenceKind =
  | 'strategy_lab_artifact_v1'
  | 'helper_pre_envelope'
  | 'report_evidence';

export type StrategyLabReviewAvailability = 'available' | 'missing' | 'invalid_json';

export interface StrategyLabReviewSource {
  id: string;
  label: string;
  evidence_kind: StrategyLabReviewEvidenceKind;
  authoritative: boolean;
  source_path: string;
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
      'No Cockpit artifact persistence store, review decision queue, or promotion workflow is implemented.',
      'No DB, Qdrant, memory, news, canonical financial truth, paper trading, or live trading write path is used.',
    ],
  };
}
