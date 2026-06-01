---
job_id: extraction_ctm_source_period_type_correction_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_ctm_source_period_type_correction_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_ctm_source_period_type_correction_v1_20260601/README.md
  - reports/agent_jobs/extraction_ctm_source_period_type_correction_v1_20260601/status.json
  - reports/agent_jobs/extraction_ctm_source_period_type_correction_v1_20260601/validation.json
  - reports/agent_jobs/extraction_ctm_source_period_type_correction_v1_20260601/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_ctm_source_period_type_correction_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: code_fix
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User approved full production runtime necessary to complete the extraction goal and then instructed Codex to proceed. This card is a bounded code fix for the CTM blocker exposed by that approved canary route."
---

# Extraction CTM Source Period Type Correction V1

## Objective

Fix the CTM hard stop from the remaining third-canary retry without weakening
validation gates.

Observed blocker:

`validation_gate:period_source_mismatch:payload=H:source=A:year_ended_source_phrase`

The source document explicitly says the report is for the year ended
31 December 2025, but Pass 1 classified the payload period type as half-year.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION.

Intended files: this task card, `multipass_extraction.py`, focused multipass
tests, `docs/claude/STATE.md`, and this report bundle.

Contested surfaces touched: none from the repo contested-surface list.

Collision risk: HIGH because this changes financial-truth extraction payload
period semantics. Proceed only after a clean registry/overlap check and keep the
change source-backed and bounded.

Decision: proceed after validation, overlap check, and registry claim.

## Contract Check

Target system layer: backend Metric Extraction payload preparation, before
Storage validation.

Relevant contract rules: backend is sole authority; pipeline order is
mandatory; extraction may use only explicit source values; no inference,
substitution, fabrication, gap filling, direct datastore mutation, alternate
pipeline, broad backfill, or validation-gate bypass is allowed.

What must not change: source PDFs, parser routing, prompts, schema/migrations,
metric values, metric ontology, Qdrant/news/memory stores, Cockpit UI, GitHub
state, direct DB rows, and fail-closed mismatch validation for unresolved
conflicts.

Why safe: the correction may use only unambiguous typed source period-end
evidence already extracted from explicit front-matter phrases, records correction
provenance in the payload, and leaves validation gates intact for missing,
ambiguous, or still-conflicting evidence.

GPU process check required: no runtime execution in this card. A read-only GPU
guard check may be recorded as environment evidence.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_ctm_source_period_type_correction_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_ctm_source_period_type_correction_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_ctm_source_period_type_correction_v1_20260601.md --repo-root .`
- Focused pytest for the new period correction regression.
- Full `financial-engine_v2/backend/tests/test_multipass_extraction.py`.
- Existing pre-canary/capability guard tests.
- Targeted Ruff.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_ctm_source_period_type_correction_v1_20260601.md --repo-root .`
- Registry release and final list-active.
