---
job_id: approved15_broad_accurate_extraction_v1_20260708
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/approved15_broad_accurate_extraction_v1_20260708.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/TASK_CARD.md
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/README.md
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/STATE.md
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/DECISIONS.md
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/VALIDATION.md
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/NEXT_GOAL.md
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/LEDGER_ENTRY_CLAIMED.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/LEDGER_ENTRY_IMPLEMENTATION_STARTED.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/LEDGER_ENTRY_CLOSEOUT.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/guard_preflight.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/registry_active_jobs.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/task_ledger_validate.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/task_ledger_search.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/github_issues_readonly.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/task_card_validate.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/diff-check.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/report_artifacts_check.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/diff-whitespace.log
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/scripts/build_failure_matrix.py
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/measurement_no_write_replay/input_manifest.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/measurement_no_write_replay/replay_results.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/measurement_no_write_replay/side_effect_audit.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/measurement_no_write_replay/validation.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/measurement_no_write_replay/logs/replay.log
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/actual_payload_map_full.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/payload_scorecard_full.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/scorecard_gate_full.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/failure_class_summary_full.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/row_level_failure_matrix_full.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/top_failure_class.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/source_bound_probe.md
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/scorecard_build.log
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/focused_unit_test_red.log
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/focused_unit_test_green.log
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/focused_replay_green/input_manifest.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/focused_replay_green/replay_results.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/focused_replay_green/side_effect_audit.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/focused_replay_green/validation.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/focused_replay_green/logs/replay.log
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/actual_payload_map_green.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/payload_scorecard_green.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/scorecard_gate_green.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/failure_class_summary_green.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/row_level_failure_matrix_green.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/top_failure_class_green.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/full_replay_green/input_manifest.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/full_replay_green/replay_results.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/full_replay_green/side_effect_audit.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/full_replay_green/validation.json
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/full_replay_green/logs/replay.log
  - reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708/scorecard_build_green.log
approval_required: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/approved15_broad_accurate_extraction_v1_20260708
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
live_ledger_mutation_allowed: false
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
docs_changed: []
docs_followup: "none"
reason: "Measurement-first issue #97 approved-15 extraction lane. Scope is limited to current-canonical no-write fixture replay, row-level failure-class matrix, and at most one source-proven deterministic code/test repair. No source-PDF, gold-label, prompt, model, runtime/data, service, GitHub, registry, or production-data mutation is allowed."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial Truth replay repair needs deterministic source/provenance reasoning, payload scorecard discipline, and strict boundary control."
worker_model_allowed: false
worker_decision_limit: "No workers planned; measurement, source proof, and one possible fix stay serialized in this worktree."
escalation_needed: false
task_scope: safe_extension
publish_approval: "USER_APPROVED_2026-07-09: proceed with preserving/publishing the grouped cashflow capex fix as a commit, push, and draft PR if safe."
---

# Approved-15 Broad Accurate Extraction

## Objective

Measure the full current-canonical approved-15 confirmed-metric replay surface,
build a row-level failure-class matrix, rank the remaining blockers, and
implement exactly one top-ranked source-proven deterministic fix if the evidence
supports a code/test repair inside the allowed files.

If the current-canonical full approved-15 replay and scorecard already pass,
stop and recommend pivoting the next lane to issue #96 runtime coverage
measurement instead of inventing a parser fix.

## Starting Evidence

- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1` at PR #487
  merge `c1f0c0a9c09fcee39af0990877dceb313147ec53`.
- Latest four-case native-currency slice was reported green, but it is not a
  broad accuracy claim.
- Current issue #97 priority is fixture accuracy and payload scorecard trust.

## Required Measurement

Use the full manifest:

- `financial-engine_v2/data/extraction_no_write_cases/approved15_current_origin_cases_v1.json`

Build these report-local artifacts only:

- no-write replay output under `measurement_no_write_replay/`
- `actual_payload_map_full.json`
- `payload_scorecard_full.json`
- `scorecard_gate_full.json`
- `failure_class_summary_full.json`
- `row_level_failure_matrix_full.json`

The row-level matrix must include:

- `case_id`
- `ticker`
- `document_type`
- `metric`
- `expected`
- `actual`
- `result_class`
- `row_ref`
- `provenance`
- `source_bound`
- `parser_backend`
- `failure_class`
- `recommended_action`

Rank repairs in this order:

1. wrong values with source-bound row-selection/table-selection proof
2. missing expected metrics where source rows are already extracted
3. not-evaluated payload gaps caused by replay/payload plumbing
4. ambiguous quarantines requiring source/gold review

## Hard Stops

- No DB, Qdrant, Redis, news, memory, backfill, source-PDF, gold-label,
  extraction-prompt, model, GPU, service-config, runtime-state, Docker-volume,
  or production-data mutation.
- No broad parser rewrite, ontology expansion, manifest expectation mutation,
  branch cleanup/deletion, merge, rebase, cherry-pick, push, reset, stash,
  clean, GitHub write, registry write, source-PDF mutation, or gold-label
  mutation.
- Do not combine more than one failure-class repair in this task.
- Do not relax fail-closed source/provenance gates globally.

## Validation

- Repo identity checks and portable Tenn guard preflight.
- Task-card validation and allowed-file diff check.
- Task-ledger validation and duplicate-work search.
- Read-only registry inspection.
- Full approved-15 no-write replay with temp `DATA_ROOT/cache/output`.
- Full payload scorecard and gate rebuild from current replay payloads.
- Focused red/green unit test if a source-proven fix is implemented.
- Focused affected-case replay after any fix.
- Full approved-15 no-write replay and scorecard gate after any fix.
- `git diff --check`.
- Report artifact and task-card diff checks.
