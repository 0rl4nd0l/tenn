---
job_id: extraction_canary_advisory_candidate_exclusion_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Query Orchestration
  - Provenance
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - reports/agent_jobs/extraction_canary_advisory_candidate_exclusion_v1_20260529/README.md
  - reports/agent_jobs/extraction_canary_advisory_candidate_exclusion_v1_20260529/status.json
  - reports/agent_jobs/extraction_canary_advisory_candidate_exclusion_v1_20260529/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_canary_advisory_candidate_exclusion_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Extraction Canary Advisory Candidate Exclusion

## Objective

Move advisory-only document blocking upstream into the #96 canary candidate
manifest path. Advisory-only documents must not enter the generated candidate
manifest as `canary_candidate` or `retry_candidate`, and the manifest must emit
an explicit exclusion/quarantine reason for operator review.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-canary-advisory-selection-v1-20260529`.
- Branch: `contain/extraction-canary-advisory-selection-v1-20260529`.
- Base HEAD: `19c3b7e7d3e85eef468ef0b0b0de6f98ec2608ff`.
- Intended files: this task card, terminal candidate manifest helper/tests, a
  minimal shared advisory predicate exposure if needed, and this job's report
  artifacts.
- Contested surfaces touched: extraction evaluation/selector helper and existing
  multipass advisory predicate only.
- Collision risk: MEDIUM because this is Financial Truth selector-adjacent code;
  proceed only after registry validation and overlap checks pass.
- Decision: proceed after task-card validation, no active overlap, and registry
  claim.

## Contract Check

- Target system layer: Evaluation/query-orchestration metadata before extraction
  submission, with Financial Truth guard significance. This does not execute
  ingestion, extraction, storage, retrieval, analysis, or client runtime code.
- Relevant contract rules: backend remains source of truth; extraction must not
  infer, substitute, fabricate, or silently degrade; duplicate pipelines and
  hidden fallbacks are forbidden; failures/ambiguity must be surfaced.
- What must not change: DB/Qdrant/news/memory stores, canonical financial rows,
  source PDFs, parser routing, extraction prompts, gold labels, runtime/model/GPU
  config, schemas, Cockpit UI, and the existing PR #125 multipass
  pre-persistence advisory guard.
- Why safe: the change only filters report-local candidate manifest rows before
  any canary submission and records an explicit exclusion reason. PR #125's
  multipass guard remains as the second safety net if an advisory document is
  submitted by another path.
- GPU process check required: no. This task does not spawn, restart, stop, or
  depend on `llama-server` and does not run a canary.

## Required Behavior

- Detect advisory-only records from title/source text metadata before the
  manifest `candidates` list is built.
- Exclude advisory-only documents from `candidates`.
- Emit a deterministic exclusion/quarantine record with document id, ticker,
  title/path metadata, and reason `advisory_only_document`.
- Preserve non-authorizing manifest semantics: no broad backfill or canary is
  authorized by the manifest.
- Preserve PR #125's multipass advisory guard as a second safety net.
- Add focused tests proving advisory docs do not enter the candidate manifest.

## Forbidden

- Third #96 canary run.
- Broad extraction or backfill.
- Production DB writes or direct SQL mutation.
- Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Source PDF edits, moves, copies, deletes, or commits.
- Parser routing changes.
- Extraction prompt changes.
- Gold-label mutation.
- Runtime, model, or GPU config changes.
- Service restarts.
- Schema migrations.
- Cockpit UI implementation.
- Unrelated cleanup, stash, reset, delete, merge, rebase, or branch cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md --repo-root .`
- Focused pytest for touched selector/guard tests.
- `python3 -m py_compile` for touched Python files.
- Ruff for touched Python files.
- JSON validation for report artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md --repo-root .`
- Confirm no source PDFs are staged.
- Registry release and final `list-active --read-only`.
- Final git status.

## Final Report Requirements

- Branch, HEAD, and worktree.
- Task card path and registry status.
- Files changed.
- Exact validation commands and results.
- Where #96 candidate selection was changed.
- Explicit proof that advisory docs are excluded before candidate manifest
  inclusion.
- Confirmation that no canary/backfill or datastore mutation ran.
- Remaining `DATA_MISSING`.
- Files intentionally not touched.
