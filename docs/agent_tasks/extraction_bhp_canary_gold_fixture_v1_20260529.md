---
job_id: extraction_bhp_canary_gold_fixture_v1_20260529
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/bhp_a_2025-06-30_canary_regression.json
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - reports/agent_jobs/extraction_bhp_canary_gold_fixture_v1_20260529/README.md
  - reports/agent_jobs/extraction_bhp_canary_gold_fixture_v1_20260529/source_verification.json
  - reports/agent_jobs/extraction_bhp_canary_gold_fixture_v1_20260529/status.json
  - reports/agent_jobs/extraction_bhp_canary_gold_fixture_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_bhp_canary_gold_fixture_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction BHP Canary Gold Fixture V1

## Objective

Capture the #96 BHP canary output as a real-document regression guard. The
canary persisted an otherwise source-backed annual USD row but selected the
wrong BHP revenue figure. This task adds a deterministic eval fixture and a
bad-payload assertion so future scorecards do not treat that payload as trusted
financial truth.

## Scope

- Primary lane: Evaluation.
- Supporting lanes: Financial Truth and Provenance.
- Mode: SAFE EXTENSION.
- Branch: `safe/extraction-bhp-canary-gold-fixture-v1-20260529`.
- Worktree: `/home/l4nd0/tenn-extraction-bhp-canary-gold-fixture-v1-20260529`.

## Contract Check

Target system layer: Evaluation, with Financial Truth fixture labels derived
only from explicit source PDF text and an existing source-identical real-gold
corpus fixture.

Relevant contract rules: backend remains the sole authority; metric extraction
truth must use only explicit values; missing or wrong values must remain visible
as abstain/quarantine outcomes; no alternate extraction pipeline, datastore
write, parser route, prompt, schema, runtime, model, GPU, service, or Cockpit UI
change is allowed.

What must not change: production extraction/backfill behavior, canonical
financial truth persistence, DB/Qdrant/news/memory stores, source PDFs, parser
routing, extraction prompts, runtime/model/GPU/service config, schemas, Cockpit
UI, GitHub state, and canary approval packets.

Why safe: this task adds only a test fixture, focused eval assertions, and
report artifacts. The BHP source PDF path is verified to be byte-identical to
the existing curated BHP FY2025 real-gold source, and the key labelled values
are rechecked from local PDF text in this task.

GPU process check required: no. This task must not start, restart, or depend on
`llama-server` and must not run live extraction jobs.

## Source Evidence

- Canary document:
  `2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7`
- Source PDF:
  `/data/asx/docs/BHP/financial_performance/2025-08-19_bhp-appendix-4e-and-2025-annual-report_2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7.pdf`
- Existing curated real-gold source PDF:
  `/data/asx/docs/BHP/financial_performance/2025-08-19_bhp-appendix-4e-and-2025-annual-report_60ba7318-bae4-4bb7-952b-ccd01b59e0d7.pdf`
- Both source files have the same SHA256:
  `39e139174313295df56143a3cbd2c704eeb9783bdffb4706a083706d6b5a490a`
- The PDF text explicitly shows US$ million, revenue `51,262`, net operating
  cash flows `18,692`, and net debt `12,924` for the 2025 annual period.

## Hard Stops

- Do not run the third canary batch.
- Do not run BHP live extraction.
- Do not run broad backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, or memory stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change parser routing, extraction prompts, schemas, runtime/model/GPU
  config, services, Cockpit UI, or GitHub state.
- Do not add source-derived values unless they are verified from the PDF or the
  byte-identical curated real-gold fixture.

## Required Behavior

- Add a test-only BHP canary-regression fixture under
  `financial-engine_v2/backend/tests/fixtures/extraction_gold/`.
- Include only explicit source context and values.
- Add eval tests proving the source-backed BHP payload is trusted.
- Add eval tests proving the observed #96 BHP canary payload is not trusted and
  triggers `revenue:wrong`.
- Preserve existing AAU/CLV/CTM canary-regression behavior.
- Record source-verification evidence in this task's report directory.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md --repo-root .`
- PDF text extraction and SHA256 verification for labelled values.
- Focused pytest for `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`.
- Targeted Ruff for touched Python tests.
- JSON validation for fixture and report artifacts.
- `git diff --check`.
- Source PDF/new binary staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_bhp_canary_gold_fixture_v1_20260529.md --repo-root .`
- Code-reviewer pass.
- Registry release and final active-job read-only check.

## Final Report Requirements

Report branch, HEAD, worktree, task card, source evidence, files changed,
validation commands/results, registry release state, whether any runtime or
datastore mutation occurred, and the next safe step toward the #96 canary.
