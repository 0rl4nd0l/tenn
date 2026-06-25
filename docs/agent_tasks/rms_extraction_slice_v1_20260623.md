---
job_id: rms_extraction_slice_v1_20260623
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/rms_extraction_slice_v1_20260623.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/README.md
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/STATE.md
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/guard_preflight.json
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/registry_active_jobs.json
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/source_rows.json
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/rms_replay_result.json
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/rms_scorecard_before.json
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/rms_scorecard_after.json
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/validation.json
  - reports/agent_jobs/rms_extraction_slice_v1_20260623/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/rms_extraction_slice_v1_20260623
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/agent_tasks/rms_extraction_slice_v1_20260623.md
docs_changed: []
docs_followup: NONE
reason: "Approved RMS-only safe extension: finish source-proven RMS extraction rows for scale, capex, cash_end, EBIT, and NPAT without broad ontology/prompt/parser changes or canonical writes."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "RMS extraction correctness requires source row proof, focused extractor changes, replay, scorecard, and PR publication under strict Financial Truth boundaries."
worker_model_allowed: false
worker_decision_limit: "No workers planned; this is a bounded single-document source-proven slice."
escalation_needed: false
task_scope: safe_extension
---

# RMS Extraction Slice

## Objective

Finish and publish the RMS extraction slice for `RMS_H_2025-12-31`.

## Scope

- Revalidate and commit the existing RMS formal table-unit scale binding and
  PP&E/PPE-only capex recovery fix.
- Inspect exact RMS source rows/tables for `cash_end`, `ebit`, and
  `np_attributable`.
- Implement only source-proven RMS-safe extraction fixes:
  - prefer exact cash/cash-equivalents rows over cash-and-gold rows;
  - recover EBIT/NPAT only when exact source row and period/scale evidence
    exist.
- Add focused positive and negative regressions.
- Run RMS replay and RMS scorecard after changes.
- Push and open a PR; do not merge automatically.

## Hard Stops

- No broad ontology, prompt, or parser changes.
- No canonical writes.
- No DB, Qdrant, Redis, news, memory, source-PDF, gold-label, schema, model,
  GPU, or production-data mutation.
- No count-24/count-32, broad backfill, PR #318, or unrelated cleanup.
- Keep missing metrics fail-closed if exact source evidence is absent.

## Validation

- Task card validate and check-diff.
- Read-only registry inspection.
- Source row proof for RMS `cash_end`, `ebit`, and `np_attributable`.
- Focused extractor regressions.
- Full `test_multipass_extraction.py`.
- RMS no-write replay with temp data/cache/output.
- RMS scorecard before/after.
- `git diff --check`.
