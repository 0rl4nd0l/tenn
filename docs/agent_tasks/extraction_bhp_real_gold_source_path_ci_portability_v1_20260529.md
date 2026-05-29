---
job_id: extraction_bhp_real_gold_source_path_ci_portability_v1_20260529
lane: Evaluation
supporting_lanes:
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529.md
  - reports/agent_jobs/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529/README.md
  - reports/agent_jobs/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529/status.json
  - reports/agent_jobs/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529/diff-check.json
  - docs/claude/STATE.md
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_bhp_real_gold_source_path_ci_portability_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Extraction BHP Real-Gold Source Path CI Portability V1

## Objective

Apply the same CI-portable real-gold source-path validation repair to the BHP
canary fixture branch backing PR #127. The PR #127 GitHub Actions run includes
the extraction failure:

`test_extraction_gold_eval.py::test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist - FileNotFoundError: DATA_MISSING: source PDF not found`

GitHub-hosted CI does not have host-mounted `/data/asx/docs` source PDFs, so the
branch must validate source-path safety by default and preserve strict source
openability behind `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`.

## Scope

- Primary lane: Evaluation.
- Supporting lane: Provenance.
- Branch: `safe/extraction-bhp-canary-gold-fixture-v1-20260529`.
- Base PR: https://github.com/0rl4nd0l/tenn/pull/127
- Mode: SAFE EXTENSION.

## Contract Check

- Target system layer: Evaluation/Provenance test behavior for real-gold corpus
  validation.
- Relevant contract rules: missing source assets must remain explicit
  `DATA_MISSING`; source paths must stay allowlisted and local; no extraction or
  persistence path may infer facts from missing source assets.
- What must not change: production extraction/backfill behavior, DB/Qdrant/news
  /memory stores, source PDFs, canonical financial truth rows, parser routing,
  extraction prompts, runtime/model/GPU/service config, schemas, Cockpit UI,
  and GitHub issue state.
- Why safe: this task only adjusts test behavior on the BHP branch so CI does
  not require host-local source assets while strict local source availability
  remains explicitly testable.
- GPU process check required: no. This task does not start, stop, restart, or
  depend on `llama-server`.

## Required Behavior

- Default CI mode validates all real-gold `source_file` values through the
  allowlisted resolver and accepts resolver `FileNotFoundError` as environment
  `DATA_MISSING` only.
- Strict local mode with `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1` fails if any
  source file is missing from all allowlisted source roots.
- `ValueError` and `PermissionError` must remain uncaught.

## Forbidden

- Runtime reload, canary, extraction, or backfill.
- Production DB writes or direct SQL mutation.
- Qdrant, news, memory, source-PDF, or canonical-truth mutation.
- Parser routing, extraction prompt, gold-label, schema, runtime/model/GPU
  config, or Cockpit UI changes.
- GitHub issue comment/close/label/milestone mutation.

## Validation

- Task-card validate, overlap check, claim, check-diff, and release.
- Default and strict `test_extraction_gold_eval.py`.
- Ruff and `py_compile` for touched test file.
- JSON validation for report artifacts.
- `git diff --check`.
- Source PDF/new binary staging check.

## Final Report Requirements

Report branch, PR, exact CI failure addressed, files changed, validation
commands/results, confirmation that strict source-asset validation still passes
locally, confirmation that no runtime/canary/datastore/source mutation occurred,
and remaining blockers.
