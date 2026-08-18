---
job_id: extraction_metric_improvement_sprint_v1_20260622
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_metric_improvement_sprint_v1_20260622.md
  - docs/agent_tasks/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/data/extraction_no_write_cases/jay_market_update_cases_v1.json
  - financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json
  - financial-engine_v2/data/extraction_no_write_cases/whc_edu_mixed_unit_cases_v1.json
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/TASK_CARD.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/STATE.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/DECISIONS.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/WORKER_A_JAY.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/WORKER_B_DXC.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/WORKER_C_WHC.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/WORKER_D_REGRESSION.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/CODE_REVIEW.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/NEXT_GOAL.md
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/status.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/validation.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/diff-check.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/source_proof.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/post_fix_matrix.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_pre_fix_replay/input_manifest.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_pre_fix_replay/replay_results.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_pre_fix_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_pre_fix_replay/validation.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_pre_fix_replay/logs/replay.log
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_post_fix_replay/input_manifest.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_post_fix_replay/replay_results.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_post_fix_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_post_fix_replay/validation.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/jay_post_fix_replay/logs/replay.log
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/guard_replay/input_manifest.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/guard_replay/replay_results.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/guard_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/guard_replay/validation.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/guard_replay/logs/replay.log
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/whc_edu_replay/input_manifest.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/whc_edu_replay/replay_results.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/whc_edu_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/whc_edu_replay/validation.json
  - reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622/whc_edu_replay/logs/replay.log
  - reports/agent_jobs/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622/DECISIONS.md
  - reports/agent_jobs/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622/JAY_SOURCE_AUDIT.md
  - reports/agent_jobs/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622/NEXT_GOAL.md
  - reports/agent_jobs/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622/STATE.md
  - reports/agent_jobs/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622/TASK_CARD.md
  - reports/agent_jobs/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622/diff-check.json
  - reports/agent_jobs/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622/jay_source_audit.json
  - reports/agent_jobs/extraction_jay_source_bound_insufficient_metrics_audit_v1_20260622/validation.json
  - financial-engine_v2/.venv/
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/extraction_metric_improvement_sprint_v1_20260622
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - docs/agent_tasks/extraction_metric_improvement_sprint_v1_20260622.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
docs_changed: []
docs_followup: NONE
reason: "Aggressive metric extraction sprint approved by the user: integrate only source-proven JAY/DXC fixes, keep WHC report-only unless exact scale proof exists, and preserve no-write safety."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial truth gate changes require source-bound proof, no-write replay, and regression validation."
worker_model_allowed: true
worker_decision_limit: "Workers may gather evidence and propose bounded fixes; orchestrator owns final integration, validation, and PR readiness."
escalation_needed: false
---

# Metric Extraction Improvement Sprint

## Objective

Start from current `origin/migration/clean-runtime-baseline-reconstruct-v1`,
preserve the JAY audit artifact commit, then integrate only source-bound and
no-write-proven extraction improvements for the active residuals:

- JAY market-update `Net Revenue` recovery as canonical `revenue`.
- DXC `metric_label_mismatch` only if the source row proves a safe mapping.
- WHC `scale_unknown` report-only unless explicit repeated source-scale proof
  exists.

## Hard Stops

- No DB, Qdrant, Redis, news, runtime, source-PDF, gold-label, dependency, or
  service writes.
- No broad extraction, full-universe backfill, or production data mutation.
- No prompt broadening or metric inference beyond source-bound rows.
- No merge, rebase, reset, stash, clean, branch deletion, or worktree deletion.
- GitHub mutation is limited to pushing this branch and opening one draft PR
  after validation passes.

## Validation

- Task-card validation, registry preflight, and diff contract.
- Red/green JAY no-write replay if the JAY fixture is certified.
- Focused `_validate_gate` tests for any product-code change.
- Existing guard no-write replay plus WHC/EDU mixed-unit replay after
  integration.
- Report bundle with worker lane findings, docs impact, code review, and
  post-fix matrix.
