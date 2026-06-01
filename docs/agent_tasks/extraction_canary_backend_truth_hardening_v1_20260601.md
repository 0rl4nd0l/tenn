---
job_id: extraction_canary_backend_truth_hardening_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_canary_backend_truth_hardening_v1_20260601.md
  - docs/claude/STATE.md
  - docs/extraction/metric_extraction_contract.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - reports/agent_jobs/extraction_canary_backend_truth_hardening_v1_20260601/README.md
  - reports/agent_jobs/extraction_canary_backend_truth_hardening_v1_20260601/status.json
  - reports/agent_jobs/extraction_canary_backend_truth_hardening_v1_20260601/validation.json
  - reports/agent_jobs/extraction_canary_backend_truth_hardening_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_canary_backend_truth_hardening_v1_20260601/function_quality_findings.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_canary_backend_truth_hardening_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: backend_truth_hardening
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction Canary Backend Truth Hardening V1

## Objective

Harden backend metric extraction against the three source-reviewed canary
truth defects exposed by the canary actual-payload real-gold scorecard:

- AAU selected a total-comprehensive owner row instead of the explicit
  profit-after-tax source row for `np_attributable`.
- AQX promoted `Loss before income tax` to canonical `ebit`.
- ATM classified statement scale as `trillions` from summary context while
  the financial statements say they are expressed in millions of Rupiah; it
  also needs the continued income-statement owner-attributable row to remain
  available for parent-owner profit selection.

This is a code/test hardening slice only. It does not run extraction, canary,
runtime services, backfill, or mutate canonical data stores.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION.

Intended files: this task card, bounded backend extraction logic, focused
backend tests, metric contract docs, report bundle, and `docs/claude/STATE.md`.

Contested surfaces touched: none.

Collision risk: LOW. The current active registry job is an unrelated Reporting
UI job in a separate worktree. This task does not touch Cockpit control paths,
runtime services, schemas, Qdrant, memory, source PDFs, or GitHub state.

Decision: proceed after task-card validation, registry overlap check, and
claim.

## Contract Check

Target system layers: Metric Extraction and Normalization in the backend-owned
extraction pipeline.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.1 backend source of truth,
§2 mandatory flow, §3.3 explicit-only metric extraction, §3.5 normalization,
and §9.4-§9.5 GPU process boundaries.

What must not change: ingestion, storage schema, canonical financial rows,
Qdrant/vector data, prompt/model/GPU/runtime config, source PDFs, Cockpit UI,
GitHub state, broad backfill behavior, or production data stores.

Why safe: this slice accepts only explicit source rows and fail-closed label
guards. Deterministic recovery may only use values already present in the
selected income-statement markdown; it does not infer, derive, or fill gaps.
Scale normalization only recognizes explicit statement-unit text such as
`Expressed in Millions of Rupiah` / `Disajikan dalam Jutaan Rupiah`.

GPU process check required: no; this task does not spawn, restart, reload, or
depend on llama.cpp, backend, Celery, or model runtime.

Architecture check: `.cursor/rules/*` are DATA_MISSING in this checkout, so
compliance is enforced against `docs/architecture/SYSTEM_CONTRACT.md`.

## Implementation Requirements

- Add a deterministic scale detector for explicit Indonesian Rupiah million
  statement units, and make it outrank unrelated Rp-trillion summary mentions.
- Keep explicit Rp-trillion support intact when no statement-million unit is
  present.
- Merge immediate income-statement continuation tables so owner-attributable
  rows on the next page remain available to the metric extractor.
- Tighten EBIT semantics so `Profit/Loss before income tax/taxation` cannot
  populate canonical `ebit` without an explicit EBIT/operating-profit label.
- Canonical metric-extraction prompt text may be tightened only to reflect
  those explicit-only source-truth rules; existing `PROMPT_HASH` mechanics must
  record any resulting prompt hash change.
- Add deterministic `np_attributable` repair only when the selected row is a
  total-comprehensive or total-profit row and an explicit profit-after-tax or
  parent-owner profit row is present in the same selected income-statement
  markdown.
- Do not weaken validation gates or confidence gates.
- Do not introduce derived EBIT, inferred NPAT, FX conversion, or broad
  substitutions.
- Add focused regressions for AAU, AQX, and ATM source-reviewed failure
  classes.

## Hard Stops

- Do not run canary extraction.
- Do not call `POST /api/process/document/{document_id}`.
- Do not start, restart, stop, or reload backend, workers, or GPU services.
- Do not run broad extraction or backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, memory, or canonical financial truth stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change schemas/migrations, runtime/model/GPU config, services,
  Cockpit UI, or GitHub state.
- Do not use LLM output to define canonical financial truth.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_canary_backend_truth_hardening_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_canary_backend_truth_hardening_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_canary_backend_truth_hardening_v1_20260601.md --repo-root .`
- Focused pytest for `test_multipass_extraction.py` AAU/AQX/ATM regressions.
- Focused pytest for `test_extraction_pre_canary_truth_gates.py`.
- Targeted Ruff and `py_compile`.
- JSON validation for report artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_canary_backend_truth_hardening_v1_20260601.md --repo-root .`
- Registry release and final active-job read-only check.
