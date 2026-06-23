---
job_id: extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/README.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/STATE.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/guard_preflight.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/registry_active_jobs.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/pr405_status.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/issue97.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/failure_rows.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/source_inspection.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/BOARD.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/BOARD_DECISION.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/NEXT_GOAL.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/worker_summary.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/validation.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/diff-check.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/replay_results_after_fix.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/scorecard_after_fix.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/scorecard_gate_after_fix.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/failure_classes_after_fix.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/logs/replay_after_fix.log
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/logs/focused_validation.log
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/logs/focused_regression_rerun.log
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/logs/full_multipass_validation.log
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/logs/ruff_validation.log
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/raw_replay_after_fix/input_manifest.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/raw_replay_after_fix/replay_results.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/raw_replay_after_fix/side_effect_audit.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/raw_replay_after_fix/validation.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/raw_replay_after_fix/logs/replay.log
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/scored-failures-task.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/scored-failures/WORKER_TASK.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/scored-failures/WORKER_RESULT.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/scored-failures/WORKER_META.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/scored-failures/raw_output.txt
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/failclosed-fixtures-task.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/failclosed-fixtures/WORKER_TASK.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/failclosed-fixtures/WORKER_RESULT.md
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/failclosed-fixtures/WORKER_META.json
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/failclosed-fixtures/raw_output.txt
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/agent_tasks/extraction_approved_15_fixture_replay_scorecard_v1_20260623.md
  - docs/agent_tasks/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624.md
docs_changed: []
docs_followup: NONE
reason: "Owner requested review-board orchestration to fix missing metrics, wrong values, fail-closed payload blockers, and other #97 scorecard blockers after PR #405 produced a clean current 15-fixture scorecard."
task_tier: critical
recommended_model: "high reasoning plus evidence-only workers"
actual_model: "Codex GPT-5"
why_this_model: "The work is Financial Truth critical: source-bound extraction fixes must distinguish parser defects from candidate-review or gold/policy blockers."
worker_model_allowed: true
worker_decision_limit: "Evidence-only workers may inspect current report artifacts and source evidence. Codex and the review board keep final Financial Truth decisions and all edits."
escalation_needed: false
task_scope: safe_extension
---

# Approved Fixture Scorecard Blocker Orchestration

## Objective

Use a Tenn review board and bounded orchestration to classify the current #97
15-fixture scorecard blockers, then implement only source-proven extraction
fixes that reduce missing metrics, wrong values, or fail-closed payloads without
mutating canonical truth.

## Scope

- Use the current PR #405 replay/scorecard artifacts as the starting evidence.
- Produce `BOARD.md`, `BOARD_DECISION.json`, and `NEXT_GOAL.md`.
- Run evidence-only worker scouts only for source and report inspection.
- Inspect source rows/tables for scored failures and fail-closed fixtures.
- Implement narrow parser/extractor fixes only where source evidence, period,
  currency, and scale are exact.
- Keep candidate-review and ambiguous-label expectations quarantined unless
  approved gold/source review changes are explicitly authorized later.
- Re-run focused tests and a no-write replay/scorecard after fixes.

## Hard Stops

- No canonical writes.
- No DB, Qdrant, Redis, news, memory, source-PDF, prompt, gold-label, schema,
  model, GPU, or production-data mutation.
- No broad backfill.
- No count-24/count-32 claim unless a current full scorecard proves it.
- No PR #318 or unrelated cleanup.
- Do not widen metric ontology or promote candidate-review rows.
- Keep metrics fail-closed when exact source evidence is absent.

## Validation

- Task card validate, report-artifact check, and check-diff.
- Review board decision with minority objection handling.
- Focused tests for every extractor behavior change.
- Full `test_multipass_extraction.py` if shared extraction behavior changes.
- No-write replay and #97 scorecard across the approved 15 fixtures after fixes.
