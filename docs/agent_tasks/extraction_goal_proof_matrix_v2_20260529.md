---
job_id: extraction_goal_proof_matrix_v2_20260529
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md
  - reports/agent_jobs/extraction_goal_proof_matrix_v2_20260529/README.md
  - reports/agent_jobs/extraction_goal_proof_matrix_v2_20260529/objective_matrix.json
  - reports/agent_jobs/extraction_goal_proof_matrix_v2_20260529/status.json
  - reports/agent_jobs/extraction_goal_proof_matrix_v2_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_goal_proof_matrix_v2_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction Goal Proof Matrix V2

## Objective

Refresh the ten-item metric extraction objective proof matrix against the
current baseline, current runtime health, and current GitHub PR state.

This task must not run extraction, submit documents, reload services, mutate
datastores, change code, or mutate GitHub state. It records which parts of the
active goal are proven, partial, blocked, or missing.

## Lane

Primary lane: Evaluation.

## Execution Mode

SAFE EXTENSION, report-local proof matrix only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-extraction-goal-proof-matrix-v2-20260529`

Branch: `audit/extraction-goal-proof-matrix-v2-20260529`

Intended files: this task card, one report bundle under this task's output
directory, and `docs/claude/STATE.md`.

Contested surfaces touched: none from the explicit contested-surface list.

Collision risk: LOW/MEDIUM because the task is report-only but records evidence
that gates future Financial Truth/runtime decisions.

Decision: proceed after validation, overlap check, and registry claim.

## Contract Check

Target system layer: Evaluation/Provenance around extraction readiness and goal
completion evidence. This task does not invoke Extraction, Storage, Retrieval,
Analysis, or Client runtime behavior.

Relevant contract rules: backend remains the source of truth; metric extraction
must use explicit values only; no fallback, parallel pipeline, or broad
accuracy claim may be introduced; GPU-dependent extraction must not run while
GPU health is not cleanly verifiable.

What must not change: production extraction/backfill, production DB writes,
direct SQL mutation, Qdrant/news/memory mutation, source PDFs, parser routing,
extraction prompts, gold labels, schemas/migrations, runtime/model/GPU/service
config, Cockpit UI, issue tracker state, PR state, or canary execution.

Why safe: the task only records current evidence, distinguishes proven scope
from unproven completion, and leaves all runtime or GitHub actions behind
separate explicit task cards.

GPU process check required: read-only GPU evidence is required because one goal
item is an approved runtime canary. No GPU process may be spawned, restarted, or
killed by this task.

## Hard Stops

- Do not run a third canary batch.
- Do not call `POST /api/process/document/{document_id}`.
- Do not restart, stop, start, rebuild, or reload any service.
- Do not run broad extraction or backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, memory, or canonical financial truth stores.
- Do not edit, move, copy, delete, hash-rewrite, or commit source PDFs.
- Do not change parser routing, extraction prompts, gold labels, source fixture
  labels, schema, migration, runtime, model, GPU, service, or Cockpit UI files.
- Do not post GitHub comments, close issues, mark PRs ready, relabel, assign, or
  edit issue/PR bodies.
- Do not perform unrelated cleanup, stash, reset, delete, merge, rebase, or
  branch cleanup operations.

## Required Behavior

- Map each of the ten active objective items to current-turn evidence.
- Treat partial, weak, indirect, or stale evidence as not complete.
- Include current PR #129 green/draft status and stale #125-#128 status without
  mutating any PR.
- Include current runtime GPU blocker and queue/API health evidence.
- Include the known broad real-gold source-PDF validation failure separately
  from focused hardening-suite success.
- Do not mark the active goal complete.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md --repo-root .`
- `gh pr list --state open --limit 10 --json number,title,isDraft,headRefName,baseRefName,mergeable,statusCheckRollup,updatedAt,url`
- `/api/health` and `/api/queue/status` read-only probes.
- `scripts/gpu_process_guard.sh --check` and direct `nvidia-smi` blocker probe.
- Focused extraction hardening pytest suite.
- Broad real-gold eval pytest showing known source-PDF validation failure.
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_goal_proof_matrix_v2_20260529.md --repo-root .`
- Code-reviewer pass over the report-only diff.
- `python3 scripts/agent_job_registry.py release extraction_goal_proof_matrix_v2_20260529 --repo-root .`
- Final registry read-only check and git status.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, files changed, validation run
with exact results, ten-item objective status, no runtime/datastore/source/GitHub
mutation confirmation, and remaining blockers.
