---
job_id: extraction_post_pr384_validation_refresh_v1_20260623
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr384_validation_refresh_v1_20260623.md
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/TASK_CARD.md
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/STATE.md
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/DECISIONS.md
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/VALIDATION.md
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/BOARD.md
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/BOARD_DECISION.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/NEXT_GOAL.md
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/status.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/validation.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/diff-check.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/pytest_fallback_selftest.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/pytest_market_update.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/post_merge_matrix.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/jay_canonical_replay/input_manifest.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/jay_canonical_replay/replay_results.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/jay_canonical_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/jay_canonical_replay/validation.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/jay_canonical_replay/logs/replay.log
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/guard_replay/input_manifest.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/guard_replay/replay_results.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/guard_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/guard_replay/validation.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/guard_replay/logs/replay.log
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/whc_edu_replay/input_manifest.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/whc_edu_replay/replay_results.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/whc_edu_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/whc_edu_replay/validation.json
  - reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/whc_edu_replay/logs/replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/NEXT_GOAL.md
  - docs/validation_baseline.md
docs_changed: []
docs_followup: NONE
reason: "Post-merge refresh of the PR #384 metric-extraction validation gaps using the canonical branch, pytest fallback, and bounded no-write replay timeout."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial-truth extraction evidence and replay results must not be converted into product fixes without source-bound proof."
worker_model_allowed: false
worker_decision_limit: "No worker delegation; orchestrator owns evidence refresh and review-board decision."
escalation_needed: false
task_scope: report_only
---

# Post-PR384 Extraction Validation Refresh

## Objective

Refresh the metric-extraction evidence after PR #384 and PR #386 reached the
canonical branch. Confirm the validation environment remediation actually
unblocks the prior pytest and replay failures, then produce a review-board
decision for the next source-proven extraction lane.

## Hard Stops

- Do not modify product code, extraction manifests, source PDFs, gold labels,
  prompts, model files, runtime config, dependency files, DB, Qdrant, Redis,
  news, or services.
- Do not run broad extraction, count samples, full-universe extraction,
  backfills, or production writes.
- Do not infer metrics from labels alone. Any proposed product lane must cite
  exact source rows or report `NO_FIX_PROVEN` / `DATA_MISSING`.
- Do not open, push, merge, rebase, reset, stash, clean, delete branches, or
  remove worktrees.

## Validation Plan

- Validate this task card and diff scope.
- Run the pytest fallback self-test and the focused JAY market-update pytest
  target.
- Rerun certified JAY market-update no-write replay on canonical.
- Rerun compatible guard no-write replay with per-case timeout enabled.
- Rerun WHC/EDU mixed-unit no-write replay with per-case timeout enabled.
- Rebuild a report-local post-merge residual matrix from the replay artifacts.
- Run Tenn review board over the refreshed evidence and record one next action.

## Row-Proof Policy

Source rows mean the exact extracted source evidence for a metric candidate:
document ID, page/table when available, row label, period, unit/scale, value,
and row reference. DXC, WHC, or any other row issue may become a product fix
only when these rows prove a narrow canonical mapping or scale binding.
Otherwise the result stays report-only.
