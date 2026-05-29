---
job_id: extraction_real_gold_source_path_validation_baseline_v1_20260529
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_real_gold_source_path_validation_baseline_v1_20260529.md
  - reports/agent_jobs/extraction_real_gold_source_path_validation_baseline_v1_20260529/README.md
  - reports/agent_jobs/extraction_real_gold_source_path_validation_baseline_v1_20260529/status.json
  - reports/agent_jobs/extraction_real_gold_source_path_validation_baseline_v1_20260529/diff-check.json
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_real_gold_source_path_validation_baseline_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Real-Gold Source Path Validation Baseline

## Objective

Make the baseline real-gold eval test validate source-path allowlisting without
requiring every source PDF to exist under `financial-engine_v2/data` on every
host or CI runner.

The failing baseline case is the 10X real-gold corpus fixture whose
`source_file` resolves through the existing ASX source-path resolver but is not
present under the repo-local `financial-engine_v2/data` tree. The test should
still fail on malformed, disallowed, non-PDF, or non-local source paths, while
keeping strict asset-openability available when explicitly requested.

## Lane

Primary lane: Evaluation.

Supporting lanes: Financial Truth and Provenance.

## Execution Mode

SAFE EXTENSION, test/eval-only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-extraction-real-gold-source-path-validation-baseline-v1-20260529`

Branch: `safe/extraction-real-gold-source-path-validation-baseline-v1-20260529`

Issue: #96

Intended files: this task card, the focused real-gold eval test, report
artifacts, and `docs/claude/STATE.md`.

Contested surfaces touched: none.

Collision risk: LOW after registry overlap check and claim.

Decision: proceed after validation and registry claim.

## Contract Check

Target system layer: Evaluation around extraction truth validation. This does
not alter ingestion, extraction, storage, retrieval, analysis, or client
runtime behavior.

Relevant contract rules: backend remains the authority for extraction truth;
metric extraction must be explicit and source-bound; no inference,
substitution, fallback masking, canonical write, or parallel production
pipeline may be introduced.

What must not change: production extraction logic, persistence, Qdrant/news or
memory stores, source PDFs, parser routing, extraction prompts, gold labels,
runtime/model/GPU/service config, schema migrations, and Cockpit UI.

Why safe: the change only adjusts a test assertion to reuse the existing
allowlisted source resolver. Missing host-local PDFs remain visible as
`DATA_MISSING` unless strict source-asset mode is enabled; malformed and
disallowed paths still fail.

GPU process check required: no. This task does not spawn, restart, stop, or
depend on `llama-server`.

## Hard Stops

- Do not run a third canary batch.
- Do not run runtime reload.
- Do not run broad backfill.
- Do not perform production DB writes.
- Do not mutate Qdrant, news, or memory stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change parser routing.
- Do not change extraction prompts.
- Do not mutate gold labels.
- Do not change runtime, model, GPU, or service config.
- Do not implement Cockpit UI.
- Do not add schema migrations.
- Do not perform unrelated cleanup, stash, reset, delete, merge, or rebase
  operations.

## Required Behavior

- Preserve the operating-cash-flow alias assertion for the real-gold corpus.
- Validate every `source_file` with the existing local-source allowlist resolver.
- Treat `FileNotFoundError` as host-local source-asset absence only in default
  mode.
- Preserve strict source asset validation behind an explicit environment flag.
- Do not catch malformed/disallowed source-path failures.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_source_path_validation_baseline_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_source_path_validation_baseline_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_source_path_validation_baseline_v1_20260529.md`
- Focused pytest for `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- Strict focused pytest with `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`
- Focused extraction regression pytest set covering pre-canary gates,
  scorecard gates, real-gold eval, and multipass extraction.
- `python3 -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- Targeted Ruff for the touched test.
- JSON validation for generated report artifacts.
- `git diff --check`
- Source PDF/new binary staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_real_gold_source_path_validation_baseline_v1_20260529.md`
- `python3 scripts/agent_job_registry.py release extraction_real_gold_source_path_validation_baseline_v1_20260529 --repo-root .`
- Final registry read-only check and git status.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, registry status, files changed,
tests run with exact results, generated artifacts, confirmation that no
runtime/canary/backfill/datastore/source-PDF mutation ran, remaining blockers
before third canary/full accurate extraction graduation, and final git status.
