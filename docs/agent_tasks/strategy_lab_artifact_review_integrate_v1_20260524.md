---
job_id: strategy_lab_artifact_review_integrate_v1_20260524
lane: Reporting
owner: Codex
supporting_lanes:
  - Provenance
  - Evaluation
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
approval_required: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_artifact_review_integrate_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_artifact_review_integrate_v1_20260524.md
  - docs/agent_tasks/strategy_lab_artifact_review_value_layer_v1_20260524.md
  - docs/agent_tasks/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524.md
  - docs/agent_tasks/strategy_lab_artifact_review_clear_or_integrate_v1_20260524.md
  - reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/validation.json
  - reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/diff-check.json
  - reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/validation.json
  - reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/diff-check.json
  - reports/agent_jobs/strategy_lab_artifact_review_integrate_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_artifact_review_integrate_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_artifact_review_integrate_v1_20260524/validation.json
  - reports/agent_jobs/strategy_lab_artifact_review_integrate_v1_20260524/diff-check.json
  - cockpit-ui/app/api/cockpit/strategy-lab/artifacts/route.ts
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.test.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.test.tsx
  - cockpit-ui/lib/strategy-lab-status.ts
  - cockpit-ui/lib/strategy-lab-status.test.ts
  - cockpit-ui/lib/strategy-lab-artifacts.ts
  - cockpit-ui/lib/strategy-lab-artifacts-server.ts
  - cockpit-ui/lib/strategy-lab-artifacts.test.ts
---

# Strategy Lab Artifact Review Integrate v1

## Objective

Integrate the already validated read-only Strategy Lab artifact review value
layer into the canonical checkout while preserving unrelated task-card dirt.

## Scope

This safe-extension task is limited to the Strategy Lab Cockpit reporting value
layer and its report evidence. The user explicitly approved continuing after the
audit reported unrelated task-card blockers. Because canonical still contains
unrelated untracked task cards, global `check-overlap` and `check-diff` are
expected to report those unrelated files; integration safety is enforced by an
exact staged-file allowlist and by rerunning focused validation before commit.

The value layer remains repo-only and read-only. It is not real QuantDinger
transport, trading, paper trading, live trading, canonical financial truth, an
artifact store, or a store-write workflow.

## Allowed Files

Only the files listed in `allowed_files` may be staged or committed by this
integration task. Do not stage or edit unrelated task-card dirt, including:

- `docs/agent_tasks/chat_guard_canonical_review_and_csl_live_smoke_v1_20260524.md`
- `docs/agent_tasks/strategy_lab_artifact_review_integration_readiness_v1_20260524.md`

## Required Checks

- Validate this task card.
- Run registry `list-active`.
- Run registry `check-overlap` and record unrelated blocker output if present.
- Apply only the isolated Strategy Lab artifact review patch files.
- Run `git diff --check`.
- Run focused Strategy Lab Vitest, targeted ESLint, TypeScript, and Python
  Strategy Lab unittests.
- Run browser smoke if safe with existing dependencies and no production data
  mutation.
- Verify staged files are a subset of this task card's `allowed_files` before
  committing.

## Forbidden

- Do not touch, stage, remove, clean, or edit unrelated task-card blockers.
- No real QuantDinger transport/client/MCP/API implementation.
- No trading, broker, paper/live execution, tokens, market orders, or portfolio
  mutation.
- No DB, Qdrant, news, memory, canonical financial truth, artifact store, or
  promotion workflow writes.
- No parser, extraction, gold-label, runtime, model, GPU, dependency, or
  service changes.
- No dependency installation.

## Deliverables

- Commit: `chore(reporting): add strategy lab artifact review`
- `reports/agent_jobs/strategy_lab_artifact_review_integrate_v1_20260524/README.md`
- `reports/agent_jobs/strategy_lab_artifact_review_integrate_v1_20260524/status.json`
