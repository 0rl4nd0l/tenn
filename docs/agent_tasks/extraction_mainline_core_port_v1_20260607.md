---
job_id: extraction_mainline_core_port_v1_20260607
lane: "Financial Truth"
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_mainline_core_port_v1_20260607.md
  - docs/extraction/metric_extraction_contract.md
  - financial-engine_v2/backend/app/core/config.py
  - financial-engine_v2/backend/app/models/asx_financials.py
  - financial-engine_v2/backend/app/alembic/versions/0004_periodic_financials_period_start_currency.py
  - financial-engine_v2/backend/app/alembic/versions/0005_add_total_equity_interest_expense.py
  - financial-engine_v2/backend/app/alembic/versions/0008_asx_structured_created_at.py
  - financial-engine_v2/backend/app/services/docling_extract.py
  - financial-engine_v2/backend/app/services/extraction_run_observability.py
  - financial-engine_v2/backend/app/services/llamacpp_runtime.py
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/app/services/prompt_registry.py
  - financial-engine_v2/backend/requirements.txt
  - financial-engine_v2/backend/tests/test_docling_extract.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - financial-engine_v2/backend/tests/test_extraction_run_observability.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - reports/agent_jobs/extraction_mainline_core_port_v1_20260607/README.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_mainline_core_port_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Port the current source-bound multipass extraction core from the migration
baseline onto the mainline stack, without broad branch merge, source-PDF writes,
DB writes, prompt mutation, or degraded/stub extraction behavior.

# Background

Live issues #73, #96, #97, and #286 remain open. PRs #297, #299, and #301
merged extraction repairs into `migration/clean-runtime-baseline-reconstruct-v1`,
but current `origin/main` still lacks the current extraction core files. The
dirty live checkout contains a tracked `multipass_extraction.py` whose
`run_multipass_extraction()` returns a skipped dict stub; that must not be used
as the source of truth.

# Required Behavior

- Restore `run_multipass_extraction()` to the structured `MultipassResult`
  contract used by the current extraction validation harness.
- Restore `docling_extract.py` routing with PyMuPDF fallback and source-read-only
  cache placement under runtime data reports.
- Restore prompt-bundle and extraction-run observability helpers needed by the
  extraction core.
- Restore only schema/model compatibility required by the restored extractor and
  tests; do not apply migrations or mutate live DBs.
- Keep extraction truth fail-closed: no LLM output may define canonical truth
  without source-bound validation.

# Hard Boundaries

- Do not edit source PDFs, gold labels, extraction prompts, production DBs,
  Qdrant, Redis, news stores, memory stores, services, cron/timers, model/GPU
  config, or runtime state.
- Do not merge the migration branch wholesale.
- Do not use or copy the dirty live checkout's stubbed extraction file.
- Do not run broad extraction samples, backfills, or persistence jobs.

# Required Validation

- Validate this task card with `scripts/agent_job_contract.py`.
- Run `scripts/agent_job_registry.py list-active --read-only --repo-root .`.
- Run focused import/py_compile checks for restored extraction modules.
- Run focused multipass/docling/broad-summary tests that do not touch production
  PDFs or live DBs.
- Run `scripts/agent_job_contract.py check-diff ... --no-write-report`.
- Run `git diff --check`.

# Definition Of Done

Mainline has the current structured multipass extraction contract available
behind tests. Remaining broad validation, production extraction runs, and DB
migration application stay separate approval-gated work.
