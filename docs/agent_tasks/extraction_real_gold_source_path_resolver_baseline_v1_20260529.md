---
job_id: extraction_real_gold_source_path_resolver_baseline_v1_20260529
lane: Evaluation
supporting_lanes:
  - Provenance
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_real_gold_source_path_resolver_baseline_v1_20260529.md
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_baseline_v1_20260529/README.md
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_baseline_v1_20260529/status.json
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_baseline_v1_20260529/diff-check.json
  - docs/claude/STATE.md
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_real_gold_source_path_resolver_baseline_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Extraction Real-Gold Source Path Resolver Baseline V1

## Objective

Remove the current baseline real-gold eval test failure where corpus source
files are checked only under the repo-relative `financial-engine_v2/data/asx`
tree even when the canonical allowlisted source resolver can find the same
source PDF under mounted ASX data roots such as `/data/asx/docs`.

This is an Evaluation/Provenance fix. It must not copy, edit, stage, symlink, or
commit source PDFs.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-real-gold-source-path-resolver-v1-20260529`.
- Branch: `safe/extraction-real-gold-source-path-resolver-v1-20260529`.
- Base HEAD: `e2029835efbd2eb6425f089d703841eb20625bf7`.
- Intended files: this task card, `test_extraction_gold_eval.py`,
  `docs/claude/STATE.md`, and this job's report artifacts.
- Contested surfaces touched: none from the explicit contested-surface list.
- Collision risk: LOW after registry overlap check and claim.
- Decision: proceed only after task-card validation, overlap check, and
  registry claim.

## Contract Check

- Target system layer: Evaluation/Provenance validation for the real-gold
  corpus.
- Relevant contract rules: backend-owned extraction truth stays source-bound;
  source assets remain external evidence and must not be fabricated, copied into
  the repo, or treated as canonical writes by a test helper.
- What must not change: production extraction/backfill behavior, canonical
  financial truth persistence, DB/Qdrant/news/memory stores, source PDFs, parser
  routing, extraction prompts, metric ontology, scale/period semantics,
  runtime/model/GPU/service config, schemas, Cockpit UI, and GitHub issue state.
- Why safe: the change reuses the existing allowlisted ASX source resolver for
  a test-only source-file openability check, matching the provenance review path
  instead of adding a parallel resolver or weakening the assertion.
- GPU process check required: no. This task does not start, stop, restart, or
  depend on `llama-server`.

## Required Behavior

- Full `test_extraction_gold_eval.py` must pass on the branch without copying
  source PDFs into `financial-engine_v2/data/asx/docs`.
- The source-asset existence assertion must still fail if the allowlisted
  resolver cannot find a source file.
- The change must use an existing resolver rather than ad hoc path fallbacks.
- No canary, runtime reload, backfill, extraction job, or datastore mutation is
  authorized.

## Forbidden

- Third #96 canary run.
- Runtime reload or service restart.
- Broad extraction or backfill.
- Production DB writes or direct SQL mutation.
- Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Source PDF edits, moves, copies, deletes, symlinks, or commits.
- Parser routing changes.
- Extraction prompt changes.
- Gold-label mutation.
- Runtime, model, or GPU config changes.
- Schema migrations.
- Cockpit UI implementation.
- Unrelated cleanup, stash, reset, delete, merge, rebase, or branch cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_source_path_resolver_baseline_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_source_path_resolver_baseline_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_source_path_resolver_baseline_v1_20260529.md --repo-root .`
- `python3 -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- Full focused `test_extraction_gold_eval.py`
- Ruff for `test_extraction_gold_eval.py`
- JSON validation for report artifacts
- `git diff --check`
- raw source/PDF staging check
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_real_gold_source_path_resolver_baseline_v1_20260529.md --repo-root .`
- Registry release and final `list-active --read-only`
- Final git status

## Final Report Requirements

Report branch, HEAD, worktree, task-card path, files changed, exact validation
results, proof that the full real-gold eval test now passes, confirmation that
no source PDFs/canary/backfill/datastore/runtime mutation occurred, and
remaining blockers before full accurate extraction graduation.
