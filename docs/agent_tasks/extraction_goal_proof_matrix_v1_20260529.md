---
job_id: extraction_goal_proof_matrix_v1_20260529
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_goal_proof_matrix_v1_20260529.md
  - reports/agent_jobs/extraction_goal_proof_matrix_v1_20260529/README.md
  - reports/agent_jobs/extraction_goal_proof_matrix_v1_20260529/objective_matrix.json
  - reports/agent_jobs/extraction_goal_proof_matrix_v1_20260529/status.json
  - reports/agent_jobs/extraction_goal_proof_matrix_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_goal_proof_matrix_v1_20260529
mutation_mode: audit_only
production_data_access: false
related_issue: 96
allow_audit_code_changes: true
---

# Extraction Goal Proof Matrix

## Objective

Build a current-state proof matrix for the active metric-extraction goal without
running runtime extraction, mutating datastores, or consuming canary approval.

The matrix must preserve the full ten-item goal and distinguish proven,
partially proven, and unproven requirements from current repo, report, PR, and
validation evidence.

## Lane

Primary lane: Evaluation.

Supporting lanes: Financial Truth, Query Orchestration, and Provenance.

## Execution Mode

AUDIT MODE, report-only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-extraction-goal-proof-matrix-v1-20260529`

Branch: `safe/extraction-goal-proof-matrix-v1-20260529`

Related issue: #96

Intended files: this task card, one report bundle under this task's output
directory, and `docs/claude/STATE.md`.

Contested surfaces touched: none.

Collision risk: LOW after registry overlap check and claim.

Decision: proceed after validation and registry claim.

## Contract Check

Target system layer: Evaluation/reporting over extraction goal evidence. This
task does not alter ingestion, extraction, storage, retrieval, analysis, or
client runtime behavior.

Relevant contract rules: backend remains the authority for any future canonical
financial truth, metric extraction must remain explicit/source-bound, and
missing proof must stay `DATA_MISSING` instead of being promoted to completion.

What must not change: production extraction, runtime reload, canary execution,
DB/Qdrant/news/memory stores, source PDFs, parser routing, extraction prompts,
gold labels, schemas/migrations, GPU/model/service config, Cockpit UI, and
GitHub issue/PR state.

Why safe: the task only records current evidence and remaining proof gaps. It
does not run extraction, enqueue jobs, modify stores, alter source assets, or
change runtime behavior.

GPU process check required: no. This audit does not spawn, restart, stop, or
depend on `llama-server`.

## Hard Stops

- Do not run a third canary batch.
- Do not run runtime reload.
- Do not call `POST /api/process/document/{document_id}`.
- Do not run broad extraction or backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, memory, or canonical financial truth stores.
- Do not edit, move, copy, delete, hash-rewrite, or commit source PDFs.
- Do not change parser routing, extraction prompts, source fixture labels, or
  gold labels.
- Do not change runtime, model, GPU, service, schema, migration, or Cockpit UI
  files.
- Do not post GitHub comments, close issues, relabel, assign, or edit issue or
  PR state.
- Do not perform unrelated cleanup, stash, reset, delete, merge, rebase, or
  branch cleanup operations.

## Required Behavior

- Map all ten active objective items to concrete current evidence.
- Mark narrow tests, commits, PRs, and reports as evidence only for the scope
  they actually cover.
- Keep broad accurate extraction graduation unproven unless full current
  canary/eval evidence exists.
- Preserve the distinction between report-local scorecards and canonical write
  authorization.
- Preserve the exact future approval boundary for the third canary.
- Identify next safe steps without requiring user input unless runtime/canary
  approval is needed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_goal_proof_matrix_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_goal_proof_matrix_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_goal_proof_matrix_v1_20260529.md`
- JSON validation for generated report artifacts.
- `git diff --check`
- Raw PDF/source-data staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_goal_proof_matrix_v1_20260529.md`
- `python3 scripts/agent_job_registry.py release extraction_goal_proof_matrix_v1_20260529 --repo-root .`
- Final registry read-only check and git status.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, files changed, validation run,
which objective items are proven vs partial vs unproven, why the active goal is
not complete, confirmation that no runtime/canary/datastore/source mutation ran,
and the next safe step.
