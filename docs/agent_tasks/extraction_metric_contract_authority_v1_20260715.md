---
job_id: extraction_metric_contract_authority_v1_20260715
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_metric_contract_authority_v1_20260715.md
  - docs/extraction/metric_extraction_contract.md
  - financial-engine_v2/backend/app/services/financial_metric_contract.py
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/app/services/extraction_review.py
  - financial-engine_v2/backend/tests/test_financial_metric_contract.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_review_service.py
  - financial-engine_v2/backend/tests/test_pipeline_stages.py
  - reports/agent_jobs/extraction_metric_contract_authority_v1_20260715/README.md
  - reports/agent_jobs/extraction_metric_contract_authority_v1_20260715/STATE.md
  - reports/agent_jobs/extraction_metric_contract_authority_v1_20260715/DECISIONS.md
  - reports/agent_jobs/extraction_metric_contract_authority_v1_20260715/VALIDATION.md
  - reports/agent_jobs/extraction_metric_contract_authority_v1_20260715/CODE_REVIEW.json
  - reports/agent_jobs/extraction_metric_contract_authority_v1_20260715/NEXT_GOAL.md
  - reports/agent_jobs/extraction_metric_contract_authority_v1_20260715/RUN_OUTCOME.json
  - reports/agent_jobs/extraction_metric_contract_authority_v1_20260715/DECISION_ENTRY.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_metric_contract_authority_v1_20260715
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
closeout_scope: code_only
control_contract_version: 2
project_id: tenn
claim_id: extraction_metric_contract_authority
proof_question: Can one typed backend-owned metric registry replace duplicated production and evaluation contract maps while preserving current extraction, persistence, review, and scorecard behavior?
hypothesis_id: typed_metric_registry_single_authority_behavior_preserved_v1
program_track: offline_development
entry_state: metric_contract_duplicated_across_extraction_persistence_and_evaluation
target_transition: shared_backend_financial_metric_contract_authority
exit_predicate: Typed registry and compatibility exports are in place, duplicated maps are removed from declared callers, current parity artifacts are unchanged, focused regressions pass, and no runtime or Financial Truth behavior changes.
source_class: tenn_canonical_backend_source
dataset_version: migration_clean_runtime_baseline_af1b33eb2a5e
evidence_hash: sha256:f881a0e8947ca0159e103ce8293d6a95c114249495b903e8288bcdd148fc99b5
capabilities:
  - READ
  - REPORT_WRITE
  - CODE_EDIT
resume_only_if: Canonical metric-contract source, focused baseline evidence, or the active multipass_extraction ownership state changes after closeout.
---

# Shared Financial Metric Contract Authority

## Objective

Create one deep backend module that owns the financial metric contract interface
used by extraction, persistence, review, and evaluation. This milestone moves
definitions and imports only; it must not change extracted values, gates,
prompts, table selection, persistence behavior, scorecard classifications, or
runtime responses.

## Current evidence

- Canonical HEAD: `af1b33eb2a5e203b21338eaa0a7e1de95362ed58`.
- Baseline: 101 focused tests passed across gold eval, scorecard, review, and
  pipeline-stage suites.
- Issues #73, #96, and #97 are open; #286 and #98 are closed.
- PR #206 is open, conflicting, and classified `STALE_PRESERVE`; it is evidence
  only and must not be adopted, retargeted, edited, or closed.
- An active isolated Financial Truth lane currently owns
  `multipass_extraction.py`; do not claim or edit until that exact registry
  overlap is released or becomes safely stale under the guard.

## Required interface

The new `financial_metric_contract` module must own typed definitions for:

- canonical output fields and persisted columns;
- evaluation-only aliases and family mappings;
- allowed statement contexts as declarative metadata;
- unit kind;
- direct-source requirement;
- the sole authorized Appendix 5B capex derivation;
- provenance requirement;
- persisted-only, internal-only, planned, unsupported, and ambiguous families;
- contract status and parity metadata.

Evaluation aliases must remain evaluation-only. They do not authorize source
row matching or semantic substitution.

## Compatibility and migration

- `multipass_extraction.METRIC_FIELDS` remains a list with the same ten fields
  and order, sourced from the registry.
- Pipeline persistence writes the same twelve columns in the same order.
- Gold evaluation, scorecard, and extraction review preserve their existing
  public constants through imported compatibility names.
- The parity matrix keeps the same artifact type, status classes, rows, counts,
  and promotion gates.
- Replace private introspection of `_METRIC_SCHEMA_BY_TABLE` with the registry's
  declared internal fields; do not alter that extraction schema in this task.

## Hard stops

- Stop before source edits while any active registry job overlaps an allowed
  source or test file.
- No extraction correctness change, derivation removal, parser change,
  narrative change, schema migration, prompt/gold/source-PDF change, ontology
  expansion, runtime/data access, DB/Qdrant/queue/service mutation, or GitHub
  write.
- No files outside `allowed_files`.
- One local allowlisted commit is authorized after validation and review; no
  push, PR, merge, rebase, cleanup, or worktree deletion.

## Validation

- V2 task-card, full guard, overlap, ledger, and registry validation.
- RED contract test proving the shared registry is absent before implementation.
- New registry invariants and uniqueness tests.
- Existing gold-eval, scorecard, extraction-review, and pipeline-stage suites.
- Snapshot/equality checks for metric field order, aliases, parity rows/status
  counts, and persisted writer order.
- `py_compile`, Ruff, `git diff --check`, task-card diff validation, report
  validation, and final code review.

## Runtime proof

This is an offline architecture milestone. It does not access live output.
Runtime Functionality Proof must close as `DATA_MISSING`, and the run must use
`DONE_WITH_RISK` rather than `DONE` even when offline validation passes.
