---
job_id: strategy_lab_readonly_subsystem_maturation_v1_20260525
title: Strategy Lab read-only subsystem maturation
owner: Codex
lane: Query Orchestration
primary_lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Provenance
  - Evaluation
mutation_mode: safe_extension
approval_required: true
user_approval_captured: true
production_data_access: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525
allowed_files:
  - docs/agent_tasks/strategy_lab_readonly_subsystem_maturation_v1_20260525.md
  - docs/strategy_lab/README.md
  - docs/strategy_lab/experiment_session_envelope_v1.md
  - docs/strategy_lab/experiment_session_envelope_v1.schema.json
  - docs/strategy_lab/readonly_subsystem_boundaries_v1.md
  - docs/strategy_lab/review_queue_contract_v1.md
  - docs/strategy_lab/review_queue_v1.schema.json
  - docs/strategy_lab/review_packets_v1.md
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/README.md
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/status.json
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/validation.json
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/diff-check.json
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/scouts/review_queue_scout.md
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/scouts/provenance_ux_scout.md
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/scouts/artifact_consistency_scout.md
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/scouts/validation_regression_scout.md
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/scouts/runtime_boundary_scout.md
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/experiment_review_packet.json
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/repeatability_summary_packet.json
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/risk_summary_packet.json
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/artifact_provenance_packet.json
  - reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/cleanup_revoke_audit_packet.json
  - cockpit-ui/lib/strategy-lab-status.ts
  - cockpit-ui/lib/strategy-lab-status-server.ts
  - cockpit-ui/lib/strategy-lab-status.test.ts
  - cockpit-ui/lib/strategy-lab-artifacts.ts
  - cockpit-ui/lib/strategy-lab-artifacts-server.ts
  - cockpit-ui/lib/strategy-lab-artifacts.test.ts
  - cockpit-ui/lib/strategy-lab-review-queue.ts
  - cockpit-ui/lib/strategy-lab-review-queue-server.ts
  - cockpit-ui/lib/strategy-lab-review-queue.test.ts
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.test.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.test.tsx
  - tests/strategy_lab/test_strategy_lab_readonly_subsystem_maturation.py
---

# Strategy Lab Read-Only Subsystem Maturation v1

## Objective

Advance the existing Strategy Lab / QuantDinger proofs into a coherent,
reviewable, repository-backed analytical subsystem for analyst workflow review
while keeping it offline, non-live, non-executing, non-canonical, and blocked by
visible promotion gates.

## Evidence Inputs

Use only existing validated evidence and milestones:

- `VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY`
- `REPEATABLE_READ_ONLY_SANDBOX_RELIABILITY_VERIFIED`
- `REVIEWABLE_READ_ONLY_STRATEGY_LAB_PATH_READY_NON_LIVE`
- readonly transport contract
- repeatability matrix
- artifact envelope prototype
- review-path status/artifact UX
- zero-order, revoke, and cleanup proof
- degraded-state probes

## Required Milestones

1. Create or improve a repo-backed review queue model for repeatability,
   transport contract, runtime proof, degraded-state, review decision,
   promotion blocker, and unresolved-risk artifacts.
2. Design or implement a read-only experiment session envelope with runtime
   proof refs, reprobe refs, degraded-state refs, cleanup/revoke proof refs,
   review status, promotion blockers, timestamps, commit refs, and worktree
   refs.
3. Improve bounded Cockpit analyst workflows for review readiness, artifact
   consistency, failure-mode inspection, provenance, cleanup/revoke proof, and
   promotion gate visibility.
4. Mature the readonly transport contract only as documentation, status, and
   report semantics for retry, degraded, timeout, unavailable, cleanup, and
   future adapter seam definitions.
5. Create bounded markdown/json review/export packets if safe.
6. Expand focused validation around degraded-state honesty, missing artifacts,
   no hidden runtime assumptions, no fake online/connected semantics, no
   accidental promotion flags, no execution affordances, no canonical-truth
   drift, no order/trade-enabling language, and no secret persistence.
7. Run internal audit-only scout passes for review queue, provenance UX,
   artifact consistency, validation/regression, and runtime boundary evidence.

## Required Boundaries

Preserve these values in every exposed status, packet, and UI surface:

- `current_sidecar_available=false`
- `execution_allowed=false`
- `canonical_financial_truth=false`
- `real_transport=false`
- `review_status=PENDING_REVIEW`
- `source_mode=repo_artifacts_only`

## Forbidden

- No broker credentials.
- No live trading.
- No paper orders.
- No execution surfaces.
- No `current_sidecar_available=true`.
- No `execution_allowed=true`.
- No `canonical_financial_truth=true`.
- No backend runtime orchestration.
- No persistent sidecar runtime.
- No MCP or live transport implementation.
- No Tenn DB, Qdrant, news, memory, source-registry, parser, runtime, model, or
  GPU configuration writes.
- No production data access.
- No destructive git operations.
- No hidden secrets or tokens.
- No misleading `ONLINE` or `CONNECTED` semantics.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_readonly_subsystem_maturation_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_readonly_subsystem_maturation_v1_20260525.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/strategy_lab_readonly_subsystem_maturation_v1_20260525.md`
- Focused Strategy Lab Vitest.
- Cockpit UI TypeScript.
- Targeted ESLint.
- Focused Python Strategy Lab regression tests.
- JSON validation for schemas, status, and packets.
- Secret scan.
- Forbidden-promotion grep.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_readonly_subsystem_maturation_v1_20260525.md --repo-root .`
- Registry release.

## Done Criteria

Strategy Lab is reviewable as a repository-artifact-backed analytical subsystem
with queue semantics, experiment session semantics, review/export packets,
provenance visibility, and failure/promotion gates, while remaining explicitly
offline, non-executing, non-canonical, and blocked from current availability or
transport promotion.
