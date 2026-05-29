---
job_id: extraction_aau_canary_failure_gold_fixture_v1_20260529
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/aau_a_2025-12-31_canary_regression.json
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529/README.md
  - reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529/source_verification.json
  - reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529/status.json
  - reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction AAU Canary Failure Gold Fixture V1

## Objective

Capture the approved #96 third-canary AAU failure as a hand-verified
real-document regression fixture so the period-end blocker and source metrics are
covered by the eval corpus before any further canary or graduation claim.

## Scope

- Primary lane: Evaluation.
- Supporting lanes: Financial Truth and Provenance.
- Mode: SAFE EXTENSION.
- Branch: `safe/extraction-aau-canary-gold-fixture-v1-20260529`.
- Worktree: `/home/l4nd0/tenn-aau-canary-gold-fixture-v1-20260529`.

## Contract Check

Target system layer: Evaluation, with Financial Truth fixture labels derived
from explicit source PDF text and rendered-page inspection.

Relevant contract rules: backend remains the sole authority; metric extraction
truth must use only explicit source values; missing or ambiguous context must
fail visibly; no alternate extraction pipeline, datastore write, parser route,
prompt, schema, runtime, model, GPU, service, or Cockpit UI change is allowed.

What must not change: production extraction/backfill behavior, canonical
financial truth persistence, DB/Qdrant/news/memory stores, source PDFs,
parser routing, extraction prompts, runtime/model/GPU/service config, schemas,
Cockpit UI, GitHub state, and the approved canary packet.

Why safe: this task adds only a test fixture, focused eval tests, and report
artifacts. The fixture is labelled from local source PDF evidence and is used by
deterministic in-memory eval helpers only.

GPU process check required: no. This task must not start, restart, or depend on
`llama-server` and must not run live extraction jobs.

## Source Evidence

- Canary document:
  `508fc892-ae88-45ec-981f-cd9e124c8375`
- Source PDF:
  `/data/asx/docs/AAU/financial_performance/2026-03-31_annual-report-and-full-year-statutory-accounts_508fc892-ae88-45ec-981f-cd9e124c8375.pdf`
- The PDF front matter explicitly says:
  `FOR THE YEAR ENDED 31 DECEMBER 2025`
- The financial statements explicitly present US dollar raw-unit values for the
  year ended 31 December 2025.

## Hard Stops

- Do not run the third canary batch.
- Do not run AAU live extraction.
- Do not run broad backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, or memory stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change parser routing, extraction prompts, schemas, runtime/model/GPU
  config, services, Cockpit UI, or GitHub state.
- Do not add source-derived values unless they are verified from the PDF.

## Required Behavior

- Add a test-only AAU canary-regression fixture under
  `financial-engine_v2/backend/tests/fixtures/extraction_gold/`.
- Include only explicit source context and values.
- Add eval tests proving the good payload is trusted and the historical missing
  `period_end` payload quarantines with `context_mismatch:period_end`.
- Preserve existing CLV/CTM canary-regression behavior.
- Record the source-verification evidence in this task's report directory.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md --repo-root .`
- PDF text extraction plus rendered-page inspection for labelled values.
- Focused pytest for `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`.
- Targeted Ruff for touched Python tests.
- JSON validation for fixture and report artifacts.
- `git diff --check`.
- Source PDF/new binary staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md --repo-root .`
- Code-reviewer pass.
- Registry release and final active-job read-only check.

## Final Report Requirements

Report branch, HEAD, worktree, task card, source evidence, files changed,
validation commands/results, registry release state, whether any runtime or
datastore mutation occurred, and the next safe step toward the #96 canary.
