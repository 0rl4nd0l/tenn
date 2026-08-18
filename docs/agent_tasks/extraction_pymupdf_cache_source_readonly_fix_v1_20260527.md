---
job_id: extraction_pymupdf_cache_source_readonly_fix_v1_20260527
lane: Financial Truth
supporting_lanes:
  - Provenance
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md
  - reports/agent_jobs/extraction_pymupdf_cache_source_readonly_fix_v1_20260527/README.md
  - reports/agent_jobs/extraction_pymupdf_cache_source_readonly_fix_v1_20260527/status.json
  - reports/agent_jobs/extraction_pymupdf_cache_source_readonly_fix_v1_20260527/diff-check.json
  - reports/agent_jobs/extraction_pymupdf_cache_source_readonly_fix_v1_20260527/github_issue_96_comment.md
  - financial-engine_v2/backend/app/services/docling_extract.py
  - financial-engine_v2/backend/tests/test_docling_extract.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_pymupdf_cache_source_readonly_fix_v1_20260527
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_only
related_issue: 96
---

# Extraction PyMuPDF Cache Source Read-Only Fix

## Objective

Fix the issue #96 extraction canary blocker where PyMuPDF fallback cache writes
attempted to create `*.pdf.pymupdf.json` beside source PDFs under read-only
`/data/asx/docs`.

This safe extension must move PyMuPDF fallback cache files to an approved
writable cache location without changing extraction semantics, parser routing
policy, prompts, gold labels, canonical truth, DB/Qdrant/news/memory stores,
runtime/model/GPU config, source PDFs, or running another canary.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-pymupdf-cache-source-readonly-fix-v1-20260527`.
- Branch: `safe/extraction-pymupdf-cache-source-readonly-fix-v1-20260527`.
- Parent live branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Parent HEAD: `c275e3c857cadd8c88491b38c13a3af6debe2539`.
- Intended files: task card, report artifacts, `docling_extract.py`, and
  focused `test_docling_extract.py` coverage.
- Contested surfaces touched: extraction parser cache-path logic only.
- Collision risk: MEDIUM because extraction code is Financial Truth surface;
  repo-file collision risk is LOW in the isolated clean worktree if registry
  overlap checks pass.
- Decision: proceed after validation, overlap check, and registry claim.

## Contract Check

- Target system layer: Extraction/parser cache handling. No ingestion,
  retrieval, analysis, client, DB, Qdrant, memory, or canonical truth writes.
- Relevant contract rules: backend owns extraction; extraction must preserve
  source data, fail visibly, and not infer/substitute/fabricate; vector IDs,
  embedding model, retrieval authority, and truth stores must remain unchanged.
- What must not change: parser routing policy, extraction prompts, metric
  semantics, gold labels, source PDFs, runtime/model/GPU config, service state,
  schemas, DB/Qdrant/news/memory stores, and canonical financial truth.
- Why safe: the change only redirects PyMuPDF JSON cache placement away from
  the source-PDF directory to a deterministic cache path under the configured
  runtime data root. It preserves the same PyMuPDF extraction output and cache
  serialization format.
- GPU process check required: no. This task does not spawn extraction, run a
  canary, start/restart services, or depend on llama-server.

## Required Behavior

- Do not write PyMuPDF cache files beside source PDFs under `/data/asx/docs`.
- Preserve source PDFs as read-only inputs.
- Write PyMuPDF fallback cache/output to an approved writable cache directory.
- Use deterministic cache keys based on source path/content metadata where
  possible.
- Ensure cache path cannot escape its approved root.
- Preserve existing parser semantics as much as possible.
- Preserve no-canonical-truth-write behavior.
- Add focused tests that simulate a read-only source directory and prove
  fallback cache output is written elsewhere.
- Add tests asserting no `*.pdf.pymupdf.json` sidecar is created next to source
  PDFs.

## Forbidden

- Running extraction canary.
- Running broad backfill.
- Production DB writes.
- Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Parser routing policy changes.
- Extraction prompt changes.
- Gold-label mutation.
- Source PDF edits, moves, copies, deletes, or commits.
- Runtime, model, or GPU config changes.
- Service restarts.
- Cockpit UI implementation.
- Schema migrations.
- Unrelated cleanup, stash, reset, delete, merge, rebase, or branch cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md --repo-root .`
- Focused pytest for updated docling extraction cache tests.
- `python3 -m py_compile financial-engine_v2/backend/app/services/docling_extract.py financial-engine_v2/backend/tests/test_docling_extract.py`
- `python3 -m ruff check financial-engine_v2/backend/app/services/docling_extract.py financial-engine_v2/backend/tests/test_docling_extract.py`
- JSON validation for report artifacts.
- Raw PDF staging check.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md --repo-root .`
- Registry release and final list-active.
- Final `git status --short --untracked-files=all`.

## Final Report Requirements

- Branch, HEAD, and worktree.
- Task card path.
- Registry status.
- Files changed.
- Exact tests run and results.
- Root cause confirmed or revised.
- New cache path behavior.
- Why source PDFs remain read-only.
- Whether a fresh canary retry is now safe to request.
- Remaining `DATA_MISSING`.
- Final git status.
- Project Memory save recommendation.
- If GitHub auth allows, issue #96 comment result. Do not close, relabel,
  assign, milestone, or edit the issue.
