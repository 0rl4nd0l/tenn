---
job_id: extraction_canary_source_review_fixture_bridge_v1_20260601
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_canary_source_review_fixture_bridge_v1_20260601.md
  - docs/claude/STATE.md
  - docs/extraction/metric_extraction_contract.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/am5_h_2025-12-31_canary_regression.json
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/aqx_h_2025-12-31_canary_regression.json
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/atm_a_2025-12-31_canary_regression.json
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/clv_h_2026-01-31_canary_regression.json
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/crs_h_2025-12-31_canary_regression.json
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/ctm_a_2025-12-31_canary_regression.json
  - financial-engine_v2/scripts/extraction_gold_eval_scorecard.py
  - scripts/rekey_real_gold_actuals_by_source_document.py
  - scripts/test_rekey_real_gold_actuals_by_source_document.py
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/README.md
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/status.json
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/validation.json
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/function_quality_findings.json
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/source_verification.json
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/canary_actuals_real_gold_keyed.json
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/source_document_rekey_summary.json
  - reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/canary_real_gold_scorecard.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: source_review_eval_fixture_bridge
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction Canary Source Review Fixture Bridge V1

## Objective

Turn the seven accepted canary runtime payloads into source-reviewable real-gold
eval evidence without treating runtime output as truth.

This task adds hand-verified real-gold fixtures for the accepted canary source
documents that are not yet covered, adds source-document identifiers to existing
CLV/CTM canary fixtures, and adds a read-only helper to rekey exported canary
actual payloads by source document id for deterministic real-gold evaluation.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Evaluation

Execution mode: SAFE EXTENSION.

Intended files: this task card, test-only real-gold fixtures, one eval helper
script and tests, real-gold scorecard CLI filtering, metric contract docs,
report bundle, and `docs/claude/STATE.md`.

Contested surfaces touched: none.

Collision risk: LOW. This is deterministic evaluation/report tooling and
test-only source-reviewed labels. It does not touch runtime extraction,
canonical persistence, parser prompts, schemas, Qdrant, memory, Cockpit UI, or
GitHub state.

Decision: proceed after task-card validation, registry overlap check, and
claim.

## Contract Check

Target system layers: Evaluation/Reporting over backend-owned extraction
artifacts, with Financial Truth labels derived only from explicit local source
PDF evidence.

Relevant contract rules: backend remains source of truth; metric extraction and
evaluation must use explicit source values only; no inference, substitution,
fallback masking, or canonical datastore mutation is allowed.

What must not change: runtime extraction behavior, parser routing, prompts,
schemas/migrations, source PDFs, canonical financial rows, Qdrant/news/memory
stores, Cockpit UI, and GitHub state.

Why safe: fixtures are test-only eval labels verified from local PDFs, and the
helper only rewrites JSON keys for scorecard review. It does not run extraction,
does not create production gold labels, and does not authorize canonical writes
or broad backfills.

GPU process check required: no; this task does not start or depend on
llama.cpp, backend, Celery, or model runtime.

Architecture check: `.cursor/rules/*` are DATA_MISSING in this checkout, so
compliance is enforced against `docs/architecture/SYSTEM_CONTRACT.md`.

## Implementation Requirements

- Add source-reviewed real-gold canary regression fixtures for AM5, AQX, ATM,
  and CRS using only values verified from local source PDFs.
- Add `source_document_id` metadata to existing CLV and CTM canary fixtures so
  actual payloads exported by source document id can match them.
- Do not add a fixture value unless it is explicit in the source PDF.
- Keep ambiguous or unsupported metric families out of trusted expectations, or
  set them to `null` only when the source review proves the runtime payload
  should abstain.
- Add a read-only rekey helper that maps actual payloads keyed by source
  document id to real-gold fixture ids.
- Fail closed on duplicate fixture source-document ids and duplicate actual
  matches.
- Support a strict mode that requires all supplied actuals to match fixtures.
- Add a focused real-gold scorecard CLI filter so canary actuals can be scored
  against only the canary fixture subset.
- Emit report-local source verification, rekey summary, keyed actuals, and
  scorecard artifacts.
- Keep all outputs explicit that canonical writes and broad backfills remain
  unauthorized.

## Hard Stops

- Do not run canary extraction.
- Do not call `POST /api/process/document/{document_id}`.
- Do not start, restart, stop, or reload backend, workers, or GPU services.
- Do not run broad extraction or backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, memory, or canonical financial truth stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change parser routing, extraction prompts, schemas/migrations,
  runtime/model/GPU config, services, Cockpit UI, or GitHub state.
- Do not use runtime canary output as source truth for fixture labels.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_canary_source_review_fixture_bridge_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_canary_source_review_fixture_bridge_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_canary_source_review_fixture_bridge_v1_20260601.md --repo-root .`
- Source PDF text extraction for AM5, AQX, ATM, and CRS.
- Focused tests for `test_extraction_gold_eval.py`.
- Focused tests for the rekey helper.
- Rekey the seven exported canary actual payloads from the prior report bundle.
- Run a canary-only real-gold scorecard over the keyed actuals.
- JSON validation for generated report artifacts and fixtures.
- Targeted Ruff and `py_compile`.
- `git diff --check`.
- Source PDF/new binary staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_canary_source_review_fixture_bridge_v1_20260601.md --repo-root .`
- Registry release and final active-job read-only check.
