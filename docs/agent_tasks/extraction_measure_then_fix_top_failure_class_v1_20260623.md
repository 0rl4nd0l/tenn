---
job_id: extraction_measure_then_fix_top_failure_class_v1_20260623
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_measure_then_fix_top_failure_class_v1_20260623.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/TASK_CARD.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/STATE.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/DECISIONS.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/VALIDATION.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/CODE_REVIEW.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/NEXT_GOAL.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/status.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/validation.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/diff-check.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/guard_preflight.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/ledger_entry.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/runtime_coverage_denominator.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/extracted_payload_scorecard.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/failure_class_matrix.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/source_row_proof.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/implementation_decision.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/runtime_coverage_issue96/README.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/runtime_coverage_issue96/coverage.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/runtime_coverage_issue96/logs/coverage.log
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/payload_scorecard_issue97/README.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/payload_scorecard_issue97/scorecard.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/payload_scorecard_issue97/logs/scorecard.log
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/source_row_proof/DXC.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/source_row_proof/WHC.md
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/source_row_proof/proof.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/affected_replay/input_manifest.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/affected_replay/replay_results.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/affected_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/affected_replay/validation.json
  - reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/affected_replay/logs/replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - reports/agent_jobs/extraction_accuracy_explain_v1_20260623/NEXT_GOAL.md
  - reports/agent_jobs/extraction_accuracy_explain_v1_20260623/BOARD_DECISION.json
  - docs/agent_tasks/extraction_measure_then_fix_top_failure_class_v1_20260623.md
docs_changed: []
docs_followup: NONE
reason: "Measurement-first extraction sprint creates the missing current denominator and implements at most one narrow source-proven fix."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Broad financial extraction accuracy requires current runtime coverage, extracted-payload scoring, source-row proof, and fail-closed implementation discipline."
worker_model_allowed: true
worker_decision_limit: "Workers may gather read-only coverage, scorecard, and source-row evidence; orchestrator owns any implementation decision."
escalation_needed: false
task_scope: safe_validation_then_safe_extension
---

# Measurement-First Extraction Sprint

## Objective

Run the current evidence refresh before changing extraction behavior:

1. Refresh issue #96 runtime coverage read-only.
2. Refresh issue #97 extracted-payload scoring on the approved confirmed metric fixture set.
3. Produce a denominator from raw documents to scored metrics.
4. Rank failure classes by impact.
5. Run exact source-row proof for the top residuals, especially DXC
   `metric_label_mismatch` and WHC `scale_unknown/openability`.
6. Implement only the top source-proven low/medium-blast-radius fix, if one is
   proven.

## Hard Stops

- No canonical writes.
- No DB, Qdrant, Redis, news, memory, source-PDF, prompt, gold-label, schema,
  model, GPU, or runtime-config mutation.
- No PR #318 use.
- No broad backfill, full-universe extraction, or unrelated cleanup.
- No global metric mapping or broad ontology/prompt/parser change without exact
  source-row proof.
- No product code change from ambiguous evidence.

## Allowed

- Use a clean isolated worktree from current
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Start local backend/model runtime if needed for bounded validation.
- Publish the validated WHC annual-report period rebinding fix as a PR when
  explicitly requested by the owner; do not merge automatically.
- Use temp `DATA_ROOT`, cache, and output directories wherever possible.
- Write report artifacts under
  `reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/`.
- Edit only the listed extraction service/test surfaces if the top failure
  class is source-proven and the fix is low/medium blast radius.

## Required Report

- Runtime coverage denominator.
- Extracted-payload scorecard.
- Ranked failure-class matrix.
- DXC/WHC source-row proof result.
- Fix implemented, or exact reason no fix was proven.
- Tests/replays run.
- Remaining blockers.
- Whether count-24/count-32 is now justified.
