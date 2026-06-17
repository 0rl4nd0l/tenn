---
job_id: extraction_unknown_row_ref_traceability_guard_v1_20260617
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_unknown_row_ref_traceability_guard_v1_20260617.md
  - financial-engine_v2/backend/app/services/provenance.py
  - financial-engine_v2/backend/tests/test_provenance_adapter.py
  - reports/agent_jobs/extraction_unknown_row_ref_traceability_guard_v1_20260617/README.md
  - reports/agent_jobs/extraction_unknown_row_ref_traceability_guard_v1_20260617/status.json
  - reports/agent_jobs/extraction_unknown_row_ref_traceability_guard_v1_20260617/validation.json
  - reports/agent_jobs/extraction_unknown_row_ref_traceability_guard_v1_20260617/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
github_mutation_allowed: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_unknown_row_ref_traceability_guard_v1_20260617
mutation_mode: safe_extension
production_data_access: false
---

# Unknown Row-Ref Traceability Guard

## Objective

Implement one narrow issue #286 provenance consumer guard: structured
`field_provenance` entries whose `row_ref` or `excerpt` is `unknown` must not be
reported as precise provenance solely because a page tag exists.

## Scope

Base canonical branch:
`origin/migration/clean-runtime-baseline-reconstruct-v1`.

Base commit at task creation:
`f6b8a606d391f7e040aa97746098a981edb49841`.

Source evidence:
`reports/agent_jobs/extraction_saved_artifact_provenance_consumer_review_v1_20260617/`
in worktree `/home/l4nd0/tenn-saved-artifact-provenance-consumer-review-v1-20260617`.

Mode: SAFE_EXTENSION / CONSUMER_TRACEABILITY_GUARD.

## Required Change

- Add a focused regression test in
  `financial-engine_v2/backend/tests/test_provenance_adapter.py`.
- Update `financial-engine_v2/backend/app/services/provenance.py` so
  structured field provenance with `row_ref` or `excerpt` equal to `unknown`
  is downgraded or explicitly flagged as incomplete traceability.
- Preserve existing precise behavior for real row labels.
- Preserve derived/prose-note behavior.
- Do not change extraction values, metric ontology, persistence schema, or
  datastore behavior.

## Hard Stops

- No count-24 or count-32.
- No extraction rerun, random sample, broad extraction, or full ticker-universe
  extraction.
- No backfill.
- No canonical writes.
- No DB, Qdrant, Redis, news, memory, source-PDF, prompt, gold-label, schema,
  runtime, service, model, or GPU mutation.
- No PR #318 patch use.
- No GitHub issue, PR, branch, or remote mutation.
- No unrelated cleanup.

## Validation

- Focused pytest for provenance adapter unknown row-ref behavior.
- Focused pytest for existing structured field provenance behavior.
- `python3 -m py_compile financial-engine_v2/backend/app/services/provenance.py`
- Ruff on touched Python/test files if available.
- JSON validation for report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_unknown_row_ref_traceability_guard_v1_20260617.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_unknown_row_ref_traceability_guard_v1_20260617.md --repo-root .`

## Final Report Requirements

- Commit hash, if committed locally.
- Changed files.
- Validation results.
- Behavior changed.
- What this proves and does not prove.
- Next recommended step.
