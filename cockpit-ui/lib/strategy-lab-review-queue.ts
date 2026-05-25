export type StrategyLabReviewQueueGroup =
  | 'repeatability_artifacts'
  | 'transport_contract_artifacts'
  | 'runtime_proof_artifacts'
  | 'degraded_state_artifacts'
  | 'cleanup_revoke_proof'
  | 'review_decisions'
  | 'promotion_blockers'
  | 'unresolved_risks';

export type StrategyLabReviewQueueAvailability = 'available' | 'missing';
export type StrategyLabReviewQueueStatus = 'PENDING_REVIEW' | 'BLOCKED' | 'DATA_MISSING';
export type StrategyLabReviewPriority = 'P0' | 'P1' | 'P2' | 'P3';

export interface StrategyLabFileRef {
  id: string;
  label: string;
  path: string;
  summary: string;
  availability: StrategyLabReviewQueueAvailability;
}

export interface StrategyLabReviewQueueSource {
  id: string;
  label: string;
  group: StrategyLabReviewQueueGroup;
  source_path: string;
  source_label: string;
  provenance_label: string;
  priority: StrategyLabReviewPriority;
  sort_key: string;
  filter_tags: string[];
  review_status: StrategyLabReviewQueueStatus;
  decision_state: 'PENDING_REVIEW' | 'PROMOTION_BLOCKED' | 'DATA_MISSING';
  evidence_timestamp: string;
  source_commit_ref: string;
  source_worktree_ref: string;
  what_is_trustworthy: string[];
  remains_non_live: string[];
  promotion_blockers: string[];
  unresolved_risks: string[];
  data_missing: string[];
}

export interface StrategyLabReviewQueueItem extends StrategyLabReviewQueueSource {
  availability: StrategyLabReviewQueueAvailability;
}

export interface StrategyLabReviewQueueGroupSummary {
  group: StrategyLabReviewQueueGroup;
  label: string;
  total: number;
  available: number;
  pending_review: number;
  blocked: number;
  data_missing: number;
}

export interface StrategyLabExperimentSessionSource {
  session_id: string;
  label: string;
  review_status: 'PENDING_REVIEW';
  current_sidecar_available: false;
  execution_allowed: false;
  canonical_financial_truth: false;
  real_transport: false;
  session_status: 'reviewable_offline_evidence' | 'DATA_MISSING';
  source_commit_ref: string;
  source_worktree_ref: string;
  evidence_timestamps: string[];
  runtime_proof_refs: StrategyLabFileRef[];
  reprobe_refs: StrategyLabFileRef[];
  degraded_state_refs: StrategyLabFileRef[];
  cleanup_proof_refs: StrategyLabFileRef[];
  revoke_proof_refs: StrategyLabFileRef[];
  review_decision_refs: StrategyLabFileRef[];
  promotion_blockers: string[];
  unresolved_risks: string[];
  data_missing: string[];
}

export interface StrategyLabReviewPacketSource {
  id: string;
  label: string;
  packet_type:
    | 'experiment_review_packet'
    | 'repeatability_summary_packet'
    | 'risk_summary_packet'
    | 'artifact_provenance_packet'
    | 'cleanup_revoke_audit_packet';
  path: string;
  review_status: 'PENDING_REVIEW';
  source_mode: 'repo_artifacts_only';
  current_sidecar_available: false;
  execution_allowed: false;
  canonical_financial_truth: false;
  real_transport: false;
  summary: string;
  data_missing: string[];
}

export interface StrategyLabReviewPacket extends StrategyLabReviewPacketSource {
  availability: StrategyLabReviewQueueAvailability;
}

export interface StrategyLabReviewWorkflow {
  schema_version: 'cockpit_strategy_lab_review_workflow_v1';
  generated_at: string;
  source_mode: 'repo_artifacts_only';
  review_status: 'PENDING_REVIEW';
  current_sidecar_available: false;
  execution_allowed: false;
  canonical_financial_truth: false;
  real_transport: false;
  sort_options: string[];
  filter_facets: string[];
  group_summaries: StrategyLabReviewQueueGroupSummary[];
  review_queue: StrategyLabReviewQueueItem[];
  experiment_sessions: StrategyLabExperimentSessionSource[];
  export_packets: StrategyLabReviewPacket[];
  data_missing: string[];
}

export const STRATEGY_LAB_REVIEW_QUEUE_SOURCES: StrategyLabReviewQueueSource[] = [
  {
    id: 'repeatability_clean_reprobe_matrix',
    label: 'Repeatability matrix and clean re-probe validation',
    group: 'repeatability_artifacts',
    source_path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/validation.json',
    source_label: 'validation_json',
    provenance_label: 'REPEATABLE_READ_ONLY_SANDBOX_RELIABILITY_VERIFIED',
    priority: 'P0',
    sort_key: '010-repeatability-clean-reprobe',
    filter_tags: ['repeatability', 'validation', 'clean_reprobe', 'verified_readonly'],
    review_status: 'PENDING_REVIEW',
    decision_state: 'PENDING_REVIEW',
    evidence_timestamp: '2026-05-25T01:56:17Z',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: '/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1',
    what_is_trustworthy: [
      'The clean re-probe validation packet records persisted exact payload paths, candle counts, response bodies, zero-order proof, revoke proof, and cleanup proof.',
    ],
    remains_non_live: [
      'The validation packet does not prove a current running sidecar or Cockpit transport availability.',
    ],
    promotion_blockers: ['current_sidecar_available remains false', 'human review decision is still absent'],
    unresolved_risks: ['source_commit_ref is DATA_MISSING in the clean re-probe status packet'],
    data_missing: ['human_review_decision', 'current_sidecar_runtime', 'source_commit_ref'],
  },
  {
    id: 'transport_contract_offline_lifecycle',
    label: 'Readonly transport contract and lifecycle',
    group: 'transport_contract_artifacts',
    source_path: 'docs/strategy_lab/mock_transport/offline_mock_transport_lifecycle_v1.md',
    source_label: 'strategy_lab_contract',
    provenance_label: 'readonly_transport_contract',
    priority: 'P0',
    sort_key: '020-transport-contract-lifecycle',
    filter_tags: ['transport_contract', 'lifecycle', 'mock_only', 'offline'],
    review_status: 'PENDING_REVIEW',
    decision_state: 'PENDING_REVIEW',
    evidence_timestamp: 'DATA_MISSING',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: 'repo://docs/strategy_lab/mock_transport',
    what_is_trustworthy: [
      'The contract documents offline-only lifecycle states and denies service startup, token issuance, store writes, and execution.',
    ],
    remains_non_live: ['The contract is documentation and test semantics only, not a live adapter.'],
    promotion_blockers: ['no real adapter task card', 'no live transport implementation approval'],
    unresolved_risks: ['future retry and timeout budgets remain design-only'],
    data_missing: ['runtime_adapter', 'live_transport_probe', 'timeout_budget_runtime_evidence'],
  },
  {
    id: 'runtime_clean_reprobe_proof',
    label: 'Runtime proof packet',
    group: 'runtime_proof_artifacts',
    source_path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/runtime_proof.json',
    source_label: 'runtime_proof_json',
    provenance_label: 'VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY',
    priority: 'P0',
    sort_key: '030-runtime-proof',
    filter_tags: ['runtime_proof', 'loopback', 'zero_order', 'read_backtest'],
    review_status: 'PENDING_REVIEW',
    decision_state: 'PENDING_REVIEW',
    evidence_timestamp: '2026-05-25T01:53:38Z',
    source_commit_ref: 'QuantDinger:91dd4e274702552b91036e2c89018622d111faee',
    source_worktree_ref: '/tmp/tenn-quantdinger-clean-reprobe-v1-20260525/QuantDinger',
    what_is_trustworthy: [
      'The packet records loopback health, read/backtest behavior, regime detect, denial probes, token revoke, and zero-order evidence from a temporary sandbox.',
    ],
    remains_non_live: ['The sandbox was temporary and must not be surfaced as currently available.'],
    promotion_blockers: ['cleanup proof required before any current-availability discussion', 'no Cockpit transport seam'],
    unresolved_risks: ['upstream QuantDinger patch was applied only in the temporary sandbox'],
    data_missing: ['persistent_adapter_design_review', 'current_runtime_probe_after_cleanup'],
  },
  {
    id: 'degraded_sidecar_unavailable_fixture',
    label: 'Sidecar unavailable degraded-state fixture',
    group: 'degraded_state_artifacts',
    source_path: 'docs/strategy_lab/mock_transport_fixtures/invalid_sidecar_unavailable_transport_response_v1.json',
    source_label: 'mock_degraded_fixture',
    provenance_label: 'degraded-state probe',
    priority: 'P1',
    sort_key: '040-degraded-sidecar-unavailable',
    filter_tags: ['degraded_state', 'sidecar_unavailable', 'DATA_MISSING', 'fixture'],
    review_status: 'PENDING_REVIEW',
    decision_state: 'PENDING_REVIEW',
    evidence_timestamp: 'DATA_MISSING',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: 'repo://docs/strategy_lab/mock_transport_fixtures',
    what_is_trustworthy: [
      'The fixture preserves unavailable behavior as a quarantined local mock result with no artifact emission.',
    ],
    remains_non_live: ['It is a mock degraded-state fixture, not a current endpoint result.'],
    promotion_blockers: ['runtime unavailable behavior must remain DATA_MISSING until separately approved'],
    unresolved_risks: ['no current unavailable smoke was run in this maturation task'],
    data_missing: ['current_unavailable_probe', 'live_endpoint_status'],
  },
  {
    id: 'degraded_timeout_fixture',
    label: 'Timeout degraded-state fixture',
    group: 'degraded_state_artifacts',
    source_path: 'docs/strategy_lab/mock_transport_fixtures/invalid_timeout_transport_response_v1.json',
    source_label: 'mock_degraded_fixture',
    provenance_label: 'degraded-state probe',
    priority: 'P1',
    sort_key: '041-degraded-timeout',
    filter_tags: ['degraded_state', 'timeout', 'DATA_MISSING', 'fixture'],
    review_status: 'PENDING_REVIEW',
    decision_state: 'PENDING_REVIEW',
    evidence_timestamp: 'DATA_MISSING',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: 'repo://docs/strategy_lab/mock_transport_fixtures',
    what_is_trustworthy: [
      'The fixture models timeout as no artifact emitted and a quarantined result status.',
    ],
    remains_non_live: ['It is simulated timeout semantics only.'],
    promotion_blockers: ['real timeout budget and retry behavior are not implemented'],
    unresolved_risks: ['timeout retry policy remains documentation/status semantics only'],
    data_missing: ['real_timeout_budget', 'retry_attempt_evidence'],
  },
  {
    id: 'cleanup_revoke_zero_order_packet',
    label: 'Cleanup, revoke, and zero-order proof',
    group: 'cleanup_revoke_proof',
    source_path: 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/cleanup_proof.json',
    source_label: 'cleanup_proof_json',
    provenance_label: 'zero-order/revoke/cleanup proof',
    priority: 'P0',
    sort_key: '050-cleanup-revoke-zero-order',
    filter_tags: ['cleanup', 'revoke', 'zero_order', 'sandbox_removed'],
    review_status: 'PENDING_REVIEW',
    decision_state: 'PENDING_REVIEW',
    evidence_timestamp: '2026-05-25T01:54:24Z',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: '/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1',
    what_is_trustworthy: [
      'Cleanup proof records containers, volumes, network, image, listeners, and temp sandbox removed after the probe.',
    ],
    remains_non_live: ['Cleanup proof is the reason current_sidecar_available must remain false.'],
    promotion_blockers: ['no persistent runtime approval', 'no post-cleanup current capability'],
    unresolved_risks: ['cleanup proof is historical and must not be reused as a current listener check'],
    data_missing: ['current_listener_probe_for_this_task'],
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
    filter_tags: ['review_decision', 'PENDING_REVIEW', 'DATA_MISSING'],
    review_status: 'DATA_MISSING',
    decision_state: 'DATA_MISSING',
    evidence_timestamp: 'DATA_MISSING',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: 'DATA_MISSING',
    what_is_trustworthy: [
      'No human review decision is present, so all Strategy Lab results must remain PENDING_REVIEW.',
    ],
    remains_non_live: ['Absent review decision blocks promotion to current availability, execution, stores, or canonical truth.'],
    promotion_blockers: ['human review decision absent'],
    unresolved_risks: ['review owner and review SLA are not encoded in repo artifacts'],
    data_missing: ['review_owner', 'review_decision', 'reviewed_at'],
  },
  {
    id: 'promotion_gate_bundle',
    label: 'Promotion gate bundle',
    group: 'promotion_blockers',
    source_path: 'docs/strategy_lab/review_queue_contract_v1.md',
    source_label: 'promotion_gate_contract',
    provenance_label: 'promotion blockers',
    priority: 'P0',
    sort_key: '070-promotion-gates',
    filter_tags: ['promotion_gate', 'blocked', 'non_live', 'non_canonical'],
    review_status: 'BLOCKED',
    decision_state: 'PROMOTION_BLOCKED',
    evidence_timestamp: 'DATA_MISSING',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: 'repo://docs/strategy_lab',
    what_is_trustworthy: [
      'Promotion is blocked unless a later task explicitly authorizes a safe readonly seam and keeps forbidden surfaces off.',
    ],
    remains_non_live: ['All promotion gates preserve current_sidecar_available=false and execution_allowed=false.'],
    promotion_blockers: [
      'current_sidecar_available=false',
      'execution_allowed=false',
      'canonical_financial_truth=false',
      'real_transport=false',
      'no persistent sidecar runtime',
      'no human review decision',
    ],
    unresolved_risks: ['future adapter seam must be separately task-carded and reviewed'],
    data_missing: ['approved_adapter_task_card', 'review_decision', 'runtime_boundary_review'],
  },
  {
    id: 'unresolved_risk_register',
    label: 'Unresolved risk register',
    group: 'unresolved_risks',
    source_path: 'reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/risk_summary_packet.json',
    source_label: 'risk_summary_packet',
    provenance_label: 'unresolved risks',
    priority: 'P1',
    sort_key: '080-unresolved-risks',
    filter_tags: ['risk', 'DATA_MISSING', 'promotion_blocker'],
    review_status: 'PENDING_REVIEW',
    decision_state: 'PENDING_REVIEW',
    evidence_timestamp: '2026-05-25T04:48:03Z',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: '/home/l4nd0/tenn-strategy-lab-readonly-subsystem-maturation-v1-20260525',
    what_is_trustworthy: [
      'The risk packet is repo-backed and names the open non-live risks without enabling them.',
    ],
    remains_non_live: ['Risks are informational review blockers only.'],
    promotion_blockers: ['all unresolved risks require explicit later approval'],
    unresolved_risks: ['review packet is a report artifact, not a runtime capability'],
    data_missing: ['post-commit final commit ref until this work is committed'],
  },
];

export const STRATEGY_LAB_REVIEW_PACKETS: StrategyLabReviewPacketSource[] = [
  {
    id: 'experiment_review_packet',
    label: 'Experiment review packet',
    packet_type: 'experiment_review_packet',
    path: 'reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/experiment_review_packet.json',
    review_status: 'PENDING_REVIEW',
    source_mode: 'repo_artifacts_only',
    current_sidecar_available: false,
    execution_allowed: false,
    canonical_financial_truth: false,
    real_transport: false,
    summary: 'Offline session-level review packet for the clean read-only sandbox proof.',
    data_missing: ['review_decision', 'current_sidecar_runtime'],
  },
  {
    id: 'repeatability_summary_packet',
    label: 'Repeatability summary packet',
    packet_type: 'repeatability_summary_packet',
    path: 'reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/repeatability_summary_packet.json',
    review_status: 'PENDING_REVIEW',
    source_mode: 'repo_artifacts_only',
    current_sidecar_available: false,
    execution_allowed: false,
    canonical_financial_truth: false,
    real_transport: false,
    summary: 'Summary of repeatability, payload persistence, zero-order, revoke, and cleanup evidence.',
    data_missing: ['human_repeatability_review'],
  },
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
    summary: 'Open blocker and unresolved-risk packet for future promotion review.',
    data_missing: ['review_owner', 'promotion_decision'],
  },
  {
    id: 'artifact_provenance_packet',
    label: 'Artifact provenance packet',
    packet_type: 'artifact_provenance_packet',
    path: 'reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/artifact_provenance_packet.json',
    review_status: 'PENDING_REVIEW',
    source_mode: 'repo_artifacts_only',
    current_sidecar_available: false,
    execution_allowed: false,
    canonical_financial_truth: false,
    real_transport: false,
    summary: 'Source paths and provenance labels for review queue items and experiment refs.',
    data_missing: ['post_commit_ref'],
  },
  {
    id: 'cleanup_revoke_audit_packet',
    label: 'Cleanup and revoke audit packet',
    packet_type: 'cleanup_revoke_audit_packet',
    path: 'reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/cleanup_revoke_audit_packet.json',
    review_status: 'PENDING_REVIEW',
    source_mode: 'repo_artifacts_only',
    current_sidecar_available: false,
    execution_allowed: false,
    canonical_financial_truth: false,
    real_transport: false,
    summary: 'Cleanup, revoke, and zero-order evidence packet.',
    data_missing: ['current_listener_probe_for_this_maturation_task'],
  },
];

export function buildStrategyLabReviewWorkflow({
  generatedAt,
  reviewQueue,
  experimentSessions,
  exportPackets,
}: {
  generatedAt: string;
  reviewQueue: StrategyLabReviewQueueItem[];
  experimentSessions: StrategyLabExperimentSessionSource[];
  exportPackets: StrategyLabReviewPacket[];
}): StrategyLabReviewWorkflow {
  return {
    schema_version: 'cockpit_strategy_lab_review_workflow_v1',
    generated_at: generatedAt,
    source_mode: 'repo_artifacts_only',
    review_status: 'PENDING_REVIEW',
    current_sidecar_available: false,
    execution_allowed: false,
    canonical_financial_truth: false,
    real_transport: false,
    sort_options: ['priority_then_sort_key', 'group_then_priority', 'availability_then_priority'],
    filter_facets: ['group', 'review_status', 'availability', 'priority', 'filter_tags'],
    group_summaries: summarizeReviewQueue(reviewQueue),
    review_queue: sortReviewQueue(reviewQueue),
    experiment_sessions: experimentSessions,
    export_packets: exportPackets,
    data_missing: [
      'No human review decision exists; every item remains PENDING_REVIEW or DATA_MISSING.',
      'No current QuantDinger sidecar runtime is probed by this workflow.',
      'No real transport, persistent sidecar, execution surface, or canonical truth integration exists.',
    ],
  };
}

export function sortReviewQueue(items: StrategyLabReviewQueueItem[]): StrategyLabReviewQueueItem[] {
  return [...items].sort((left, right) => {
    const priority = priorityRank(left.priority) - priorityRank(right.priority);
    if (priority !== 0) return priority;
    return left.sort_key.localeCompare(right.sort_key);
  });
}

function summarizeReviewQueue(items: StrategyLabReviewQueueItem[]): StrategyLabReviewQueueGroupSummary[] {
  const groups = new Map<StrategyLabReviewQueueGroup, StrategyLabReviewQueueItem[]>();
  for (const item of items) {
    groups.set(item.group, [...(groups.get(item.group) ?? []), item]);
  }

  return Array.from(groups.entries())
    .map(([group, groupItems]) => ({
      group,
      label: groupLabel(group),
      total: groupItems.length,
      available: groupItems.filter((item) => item.availability === 'available').length,
      pending_review: groupItems.filter((item) => item.review_status === 'PENDING_REVIEW').length,
      blocked: groupItems.filter((item) => item.review_status === 'BLOCKED').length,
      data_missing: groupItems.filter((item) => item.review_status === 'DATA_MISSING').length,
    }))
    .sort((left, right) => groupOrder(left.group) - groupOrder(right.group));
}

export function groupLabel(group: StrategyLabReviewQueueGroup): string {
  switch (group) {
    case 'repeatability_artifacts':
      return 'Repeatability artifacts';
    case 'transport_contract_artifacts':
      return 'Transport contract artifacts';
    case 'runtime_proof_artifacts':
      return 'Runtime proof artifacts';
    case 'degraded_state_artifacts':
      return 'Degraded-state artifacts';
    case 'cleanup_revoke_proof':
      return 'Cleanup and revoke proof';
    case 'review_decisions':
      return 'Review decisions';
    case 'promotion_blockers':
      return 'Promotion blockers';
    case 'unresolved_risks':
      return 'Unresolved risks';
  }
}

function priorityRank(priority: StrategyLabReviewPriority): number {
  switch (priority) {
    case 'P0':
      return 0;
    case 'P1':
      return 1;
    case 'P2':
      return 2;
    case 'P3':
      return 3;
  }
}

function groupOrder(group: StrategyLabReviewQueueGroup): number {
  const order: StrategyLabReviewQueueGroup[] = [
    'repeatability_artifacts',
    'transport_contract_artifacts',
    'runtime_proof_artifacts',
    'degraded_state_artifacts',
    'cleanup_revoke_proof',
    'review_decisions',
    'promotion_blockers',
    'unresolved_risks',
  ];
  return order.indexOf(group);
}
