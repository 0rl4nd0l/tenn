---
job_id: extraction_real_gold_corpus_baseline_v1_20260529
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_real_gold_corpus_baseline_v1_20260529.md
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/bhp_a_2025-06-30_canary_regression.json
  - reports/agent_jobs/extraction_real_gold_corpus_baseline_v1_20260529/README.md
  - reports/agent_jobs/extraction_real_gold_corpus_baseline_v1_20260529/status.json
  - reports/agent_jobs/extraction_real_gold_corpus_baseline_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_real_gold_corpus_baseline_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Real-Gold Corpus Baseline Integration

## Objective

Integrate the already-published real-gold canary regression evidence into a
fresh isolated baseline branch without running runtime extraction or mutating
canonical stores.

This task advances the active extraction goal item to build a real-gold/eval
corpus from canary failures by adding the BHP current-period revenue regression
fixture and making the real-gold source-path validation portable across hosts.

## Lane

Primary lane: Evaluation.

Supporting lane: Financial Truth.

## Execution Mode

SAFE EXTENSION MODE.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-extraction-real-gold-corpus-baseline-v1-20260529`

Branch: `safe/extraction-real-gold-corpus-baseline-v1-20260529`

Related issue: #96

Intended files: this task card, the real-gold eval test, one BHP real-gold
fixture, this task's report bundle, and `docs/claude/STATE.md`.

Contested surfaces touched: none.

Collision risk: LOW after registry overlap check and claim.

Decision: proceed after validation and registry claim.

## Contract Check

Target system layer: Evaluation with a Financial Truth fixture. This task does
not alter ingestion, runtime extraction, storage, retrieval, analysis, or client
behavior.

Relevant contract rules: backend remains the authority for canonical financial
truth, metric extraction/evaluation must remain source-bound, no inferred
metrics may become truth, and missing source assets must be explicit rather than
silently converted into pass/fail claims.

What must not change: runtime reload, canary execution, `POST
/api/process/document/{document_id}`, broad extraction/backfill, DB/Qdrant/news
/memory stores, source PDFs, parser routing, extraction prompts, production
schemas/migrations, model/GPU/service config, Cockpit UI, and GitHub issue/PR
state.

Why safe: the task only extends test/evaluation evidence. The fixture records
hand-verified expected values for a known canary failure, and source-path
validation uses the existing allowlisted source resolver with an opt-in strict
asset gate for host environments that have the raw PDFs available.

GPU process check required: no. This task does not spawn, restart, stop, or
depend on `llama-server`.

## Hard Stops

- Do not run a third canary batch.
- Do not run runtime reload.
- Do not call `POST /api/process/document/{document_id}`.
- Do not run broad extraction or backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, memory, or canonical financial truth stores.
- Do not edit, move, copy, delete, hash-rewrite, or commit source PDFs.
- Do not change parser routing, extraction prompts, production schemas,
  migrations, runtime/model/GPU/service files, or Cockpit UI.
- Do not post GitHub comments, close issues, relabel, assign, or edit issue or
  PR state.
- Do not perform unrelated cleanup, stash, reset, delete, merge, rebase, or
  branch cleanup operations.

## Required Behavior

- Add the BHP canary regression fixture with explicit current-period expected
  values and source identity.
- Prove the source-backed BHP payload is trusted.
- Prove the historical BHP wrong-current-period revenue payload is not trusted.
- Preserve AAU, CLV, CTM, VIVA, and synthetic eval behavior.
- Replace project-root-only source asset assertions with the existing
  allowlisted source resolver.
- Keep raw source assets optional by default and strict only under
  `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_corpus_baseline_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_corpus_baseline_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_corpus_baseline_v1_20260529.md`
- Focused `test_extraction_gold_eval.py`.
- Focused guardrail/ontology/scorecard/multipass suite.
- Strict real-gold source-asset validation when source assets are present.
- `python3 -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- Targeted Ruff for touched Python test.
- JSON validation for generated artifacts and the new fixture.
- `git diff --check`.
- Raw PDF/source-data staging check.
- Sensitive string staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_real_gold_corpus_baseline_v1_20260529.md`
- `python3 scripts/agent_job_registry.py release extraction_real_gold_corpus_baseline_v1_20260529 --repo-root .`
- Final registry read-only check and git status.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, files changed, validation run,
current goal impact, confirmation that no runtime/canary/datastore/source
mutation ran, and the next safe step.
