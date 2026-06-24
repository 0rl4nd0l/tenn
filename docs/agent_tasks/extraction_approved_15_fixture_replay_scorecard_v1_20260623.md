---
job_id: extraction_approved_15_fixture_replay_scorecard_v1_20260623
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_approved_15_fixture_replay_scorecard_v1_20260623.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/README.md
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/STATE.md
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/guard_preflight.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/registry_active_jobs.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/fixture_manifest.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/source_resolution.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/replay_results_before_fix.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/replay_results.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/scorecard_before_fix.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/scorecard.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/scorecard_gate_before_fix.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/scorecard_gate.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/failure_classes_before_fix.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/failure_classes.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/validation.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/diff-check.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/logs/replay.log
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/logs/tcl_after_fix_replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/agent_tasks/extraction_approved_15_fixture_replay_scorecard_v1_20260623.md
docs_changed: []
docs_followup: NONE
reason: "Approved current 15-fixture no-write replay and #97 scorecard after PR #401 landed; report-local artifacts only, with at most one narrow source-proven extraction fix if the top failure class is proven. Merge-gate GitHub mutation approved by the owner on 2026-06-23 with 'merge if safe'."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "The job must preserve Financial Truth boundaries while running bounded no-write extraction replay, evaluating payload scorecards, ranking failure classes, and possibly making one source-proven fix."
worker_model_allowed: false
worker_decision_limit: "No workers used; replay, source inspection, code change, and validation were handled directly in this bounded task."
escalation_needed: false
task_scope: safe_execution
---

# Approved 15-Fixture Replay And #97 Scorecard

## Objective

Generate current report-local actual payloads for all 15 approved extraction
fixtures, using RMS as the already-merged completed case, then run the #97
extracted-payload scorecard across the full set.

## Scope

- Resolve all 15 approved fixture PDFs.
- Run bounded no-write replay with temp `DATA_ROOT`, cache, output, and runtime
  surfaces.
- Produce current actual payloads in report-local artifacts only.
- Run #97 extracted-payload scorecard across all 15 fixtures.
- Rank failure classes by count and evidence.
- Implement at most one top source-proven extraction fix with focused tests,
  then rescore.

## Hard Stops

- No canonical writes.
- No DB, Qdrant, Redis, news, memory, source-PDF, prompt, gold-label, schema,
  model, GPU, or production-data mutation.
- No broad backfill.
- No count-24/count-32 claim unless the full 15-fixture current scorecard
  proves it.
- No PR #318 or unrelated cleanup.
- Keep missing metrics fail-closed when source evidence is absent.

## Validation

- Task card validate and check-diff.
- Read-only registry inspection.
- Temp-data no-write replay surface audit.
- #97 scorecard and gate artifacts.
- Focused tests only if a source-proven fix is implemented.
- Full `test_multipass_extraction.py` if extractor behavior changes.
