---
job_id: extraction_qbe_revenue_selection_v1_20260629
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_qbe_revenue_selection_v1_20260629.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/TASK_CARD.md
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/README.md
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/STATE.md
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/DECISIONS.md
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/VALIDATION.md
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/NEXT_GOAL.md
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/diff-check.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/guard_preflight.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/registry_active_jobs.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/ledger_validate.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/ledger_search_qbe_revenue.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/task_card_validate.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/source_lineage_qbe.md
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/source_lineage_qbe.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/qbe_actual_payload_before_fix.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/qbe_actual_payload_after_fix.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/no_write_replay_qbe/input_manifest.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/no_write_replay_qbe/replay_results.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/no_write_replay_qbe/side_effect_audit.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/no_write_replay_qbe/validation.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/no_write_replay_qbe/logs/replay.log
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/actual_payload_map_after_qbe.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/payload_scorecard_after_qbe.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/payload_scorecard_delta_after_qbe.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/scorecard_gate_after_qbe.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/failure_classes_after_qbe.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/row_level_failure_matrix_after_qbe.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/validation/commands.log
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/validation/diff_check.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/validation/report_artifacts_check.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/validation/scorecard_after_qbe_summary.json
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/validation/pytest_qbe.log
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/validation/pytest_scorecard.log
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/handoff/HANDOFF.md
  - reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629/handoff/NEXT_GOAL.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/extraction_qbe_revenue_selection_v1_20260629
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
docs_impact: DOCS_FOLLOWUP
docs_checked:
  - AGENTS.md
  - docs/README.md
  - .agents/skills/tenn-goal-report/SKILL.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
docs_changed: []
docs_followup: "If QBE insurer revenue selection changes extraction behavior, update extraction behavior docs before PR closeout or track as a follow-up."
reason: "Continue approved-15 blocker remediation from the prior handoff, selecting only QBE formal-statement revenue selection from current origin and preserving no-write boundaries."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial Truth extraction repair requires source-bound lineage, guard checks, one narrow deterministic fix, and conservative replay evidence."
worker_model_allowed: "none"
worker_decision_limit: "no workers used; orchestrator owns final decision"
escalation_needed: false
task_scope: qbe_formal_statement_revenue_selection_only
---

# QBE Formal Statement Revenue Selection

## Objective

Start from current `origin/migration/clean-runtime-baseline-reconstruct-v1` in
a clean task worktree and investigate only the QBE approved-15 revenue blocker.
Prove the source lineage before code changes. If proven, implement at most one
narrow deterministic fix, run the focused QBE no-write replay, rebuild the
approved-15 scorecard/gate, and stop `PARTIAL` unless fully unblocked.

## Scope

- Worktree:
  `/home/l4nd0/tenn-extraction-qbe-revenue-selection-v1-20260629`
- Branch: `safe/extraction-qbe-revenue-selection-v1-20260629`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `9fdee4cdb7fbce3d925ba7d5205da75c35d59295`
- Handoff:
  `/home/l4nd0/tenn-extraction-approved15-blocker-lanes-v1-20260629/reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/handoff/HANDOFF.md`
- Selected lane: QBE formal-statement revenue selection.

## Current-Origin Note

Live evidence shows PR #465 for the prior RMS cash-flow fix is open and commit
`499f70efde4d478f26d9b5230641d3311649ac8e` is not contained in current
`origin/migration/clean-runtime-baseline-reconstruct-v1`. This task must not
redo RMS or silently depend on that branch. Any approved-15 gate rebuild must
interpret remaining RMS failures as external to this QBE lane.

## Hard Stops

- No DB, Qdrant, Redis, news, runtime, backfill, production-data, source-PDF,
  gold-label, extraction prompt, model, service, count-24/count-32, or GitHub
  issue mutation.
- No RMS rework, BHP/MIN work, DXS work, ambiguous-quarantine policy work,
  broad parser rewrite, ontology expansion, fixture rewrite, source asset
  rewrite, branch cleanup, merge, rebase, reset, stash, clean, push, or GitHub
  write.
- Do not weaken `accepted_output_scale_magnitude_risk` globally.
- Code/test mutation is limited to one narrow source-proven QBE insurer revenue
  selection behavior plus focused tests under the allowlist.

## Validation

- Repo identity checks and portable Tenn guard preflight.
- Task-card validation and read-only registry/ledger checks.
- Source lineage proof for QBE expected row and bad selected row.
- Focused pytest for any code change.
- Focused no-write replay for `QBE_H_2025-06-30`.
- Approved-15 payload scorecard/gate rebuild.
- `git diff --check`, task-card `check-diff`, and report artifact checks.
