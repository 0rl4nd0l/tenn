import { existsSync } from 'node:fs';
import path from 'node:path';

import type { StrategyLabReviewArtifact } from './strategy-lab-artifacts';
import {
  STRATEGY_LAB_REVIEW_PACKETS,
  STRATEGY_LAB_REVIEW_QUEUE_SOURCES,
  buildStrategyLabReviewWorkflow,
  type StrategyLabExperimentSessionSource,
  type StrategyLabFileRef,
  type StrategyLabReviewPacket,
  type StrategyLabReviewQueueAvailability,
  type StrategyLabReviewQueueItem,
  type StrategyLabReviewWorkflow,
} from './strategy-lab-review-queue';

export interface ReadStrategyLabReviewWorkflowOptions {
  generatedAt: string;
  workspaceRoot: string;
  artifacts: StrategyLabReviewArtifact[];
}

export function readStrategyLabReviewWorkflow({
  generatedAt,
  workspaceRoot,
  artifacts,
}: ReadStrategyLabReviewWorkflowOptions): StrategyLabReviewWorkflow {
  const reviewQueue = STRATEGY_LAB_REVIEW_QUEUE_SOURCES.map((source) => ({
    ...source,
    availability: source.source_path === 'DATA_MISSING' ? 'missing' : fileAvailability(workspaceRoot, source.source_path),
  }));
  const experimentSessions = [buildCleanReprobeExperimentSession(workspaceRoot)];
  const exportPackets = STRATEGY_LAB_REVIEW_PACKETS.map((packet): StrategyLabReviewPacket => ({
    ...packet,
    availability: fileAvailability(workspaceRoot, packet.path),
  }));

  return buildStrategyLabReviewWorkflow({
    generatedAt,
    reviewQueue: hydrateQueueFromArtifacts(reviewQueue, artifacts),
    experimentSessions,
    exportPackets,
  });
}

function buildCleanReprobeExperimentSession(workspaceRoot: string): StrategyLabExperimentSessionSource {
  const basePath = 'reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525';
  const packetBase = 'reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets';

  return {
    session_id: 'stratlab_qd_clean_reprobe_readonly_20260525',
    label: 'QuantDinger clean read-only sandbox re-probe',
    review_status: 'PENDING_REVIEW',
    current_sidecar_available: false,
    execution_allowed: false,
    canonical_financial_truth: false,
    real_transport: false,
    session_status: fileAvailability(workspaceRoot, `${basePath}/status.json`) === 'available'
      ? 'reviewable_offline_evidence'
      : 'DATA_MISSING',
    source_commit_ref: 'DATA_MISSING',
    source_worktree_ref: '/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1',
    evidence_timestamps: ['2026-05-25T01:53:38Z', '2026-05-25T01:54:24Z', '2026-05-25T01:56:17Z'],
    runtime_proof_refs: [
      fileRef(workspaceRoot, 'runtime_proof', 'Runtime proof', `${basePath}/runtime_proof.json`),
      fileRef(workspaceRoot, 'validation_log', 'Validation log', `${basePath}/validation.json`),
      fileRef(workspaceRoot, 'runtime_status', 'Runtime status', `${basePath}/status.json`),
    ],
    reprobe_refs: [
      fileRef(workspaceRoot, 'backtest_request', 'Backtest request', `${basePath}/payloads/backtest_request.json`),
      fileRef(workspaceRoot, 'backtest_response', 'Backtest response', `${basePath}/payloads/backtest_final_response.json`),
      fileRef(workspaceRoot, 'regime_request', 'Regime request', `${basePath}/payloads/regime_request.json`),
      fileRef(workspaceRoot, 'regime_response', 'Regime response', `${basePath}/payloads/regime_response.json`),
    ],
    degraded_state_refs: [
      fileRef(
        workspaceRoot,
        'sidecar_unavailable_fixture',
        'Sidecar unavailable fixture',
        'docs/strategy_lab/mock_transport_fixtures/invalid_sidecar_unavailable_transport_response_v1.json',
      ),
      fileRef(
        workspaceRoot,
        'timeout_fixture',
        'Timeout fixture',
        'docs/strategy_lab/mock_transport_fixtures/invalid_timeout_transport_response_v1.json',
      ),
    ],
    cleanup_proof_refs: [
      fileRef(workspaceRoot, 'cleanup_proof', 'Cleanup proof', `${basePath}/cleanup_proof.json`),
      fileRef(workspaceRoot, 'zero_order_proof', 'Zero-order proof', `${basePath}/payloads/zero_order_proof.json`),
    ],
    revoke_proof_refs: [
      fileRef(workspaceRoot, 'revoke_response', 'Revoke response', `${basePath}/payloads/revoke_response.json`),
      fileRef(workspaceRoot, 'post_revoke_whoami', 'Post-revoke whoami', `${basePath}/payloads/post_revoke_whoami_response.json`),
    ],
    review_decision_refs: [
      fileRef(workspaceRoot, 'experiment_review_packet', 'Experiment review packet', `${packetBase}/experiment_review_packet.json`),
      fileRef(workspaceRoot, 'risk_summary_packet', 'Risk summary packet', `${packetBase}/risk_summary_packet.json`),
    ],
    promotion_blockers: [
      'current_sidecar_available=false',
      'execution_allowed=false',
      'canonical_financial_truth=false',
      'real_transport=false',
      'human_review_decision=DATA_MISSING',
      'no persistent sidecar runtime',
      'no backend orchestration or MCP/live transport implementation',
    ],
    unresolved_risks: [
      'source_commit_ref is DATA_MISSING for the Tenn repo state that produced the clean re-probe evidence',
      'upstream QuantDinger regime fix was applied in a temporary sandbox only',
      'review/export packets are repo artifacts only and do not create an artifact store',
    ],
    data_missing: ['human_review_decision', 'current_sidecar_runtime', 'persistent_adapter', 'post_commit_ref'],
  };
}

function hydrateQueueFromArtifacts(
  reviewQueue: StrategyLabReviewQueueItem[],
  artifacts: StrategyLabReviewArtifact[],
): StrategyLabReviewQueueItem[] {
  const availabilityByPath = new Map(artifacts.map((artifact) => [artifact.source_path, artifact.availability]));

  return reviewQueue.map((item) => {
    const artifactAvailability = availabilityByPath.get(item.source_path);
    if (artifactAvailability === 'available' || artifactAvailability === 'missing') {
      return {
        ...item,
        availability: artifactAvailability,
      };
    }
    return item;
  });
}

function fileRef(workspaceRoot: string, id: string, label: string, filePath: string): StrategyLabFileRef {
  return {
    id,
    label,
    path: filePath,
    summary: `Repo artifact reference: ${filePath}`,
    availability: fileAvailability(workspaceRoot, filePath),
  };
}

function fileAvailability(workspaceRoot: string, filePath: string): StrategyLabReviewQueueAvailability {
  return existsSync(path.join(workspaceRoot, filePath)) ? 'available' : 'missing';
}
