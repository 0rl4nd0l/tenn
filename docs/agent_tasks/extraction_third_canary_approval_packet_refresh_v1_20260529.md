---
job_id: extraction_third_canary_approval_packet_refresh_v1_20260529
lane: Query Orchestration
supporting_lanes:
  - Financial Truth
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md
  - reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/README.md
  - reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/status.json
  - reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/canary_approval_packet.json
  - reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/canary_candidates.csv
  - reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction Third Canary Approval Packet Refresh V1

## Objective

Refresh the #96 bounded canary approval packet after the current truth-gate,
advisory-selection, scale-policy, ontology, period, canary-regression, and
pre-persistence scorecard-gate patches.

This task must not run a canary. It produces a report-local operator approval
packet for a future third #96 canary and makes stale prior-candidate decisions
explicit.

## Lane

Primary lane: Query Orchestration.

Supporting lanes: Financial Truth, Evaluation, and Provenance.

## Execution Mode

SAFE EXTENSION, report-local approval packet only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Issue: #96

Intended files: this task card, one report bundle under this task's output
directory, and `docs/claude/STATE.md`.

Contested surfaces touched: none from the explicit contested-surface list.

Collision risk: MEDIUM because this report controls a future financial-truth
runtime action, but this task performs no runtime, datastore, or source
mutation.

Decision: proceed after validation, overlap check, and registry claim.

## Contract Check

Target system layer: Evaluation/Provenance around canary approval and future
Extraction/Storage execution gating. This task does not invoke extraction or
storage.

Relevant contract rules: backend remains the sole authority for any future
runtime execution; metric extraction must stay explicit/source-bound; failures
and ambiguity must fail fast; no fallback, parallel pipeline, or approximation
may be introduced.

What must not change: production extraction/backfill, production DB writes,
direct SQL mutation, Qdrant/news/memory mutation, source PDFs, parser routing,
extraction prompts, gold labels, schemas/migrations, runtime/model/GPU/service
config, Cockpit UI, issue tracker state, or canary execution.

Why safe: the packet consumes current repo/report evidence only, removes stale
prior candidates that current policy would exclude, requires exact future
operator approval before execution, and keeps every future runtime side effect
behind immediate pre-run checks.

GPU process check required: no for this report-only task. A future approved
canary must run `scripts/gpu_process_guard.sh --check` before the first
extraction POST because that execution depends on `llama-server`.

## Hard Stops

- Do not run a third canary batch.
- Do not call `POST /api/process/document/{document_id}`.
- Do not run broad extraction or backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, memory, or canonical financial truth stores.
- Do not edit, move, copy, delete, hash-rewrite, or commit source PDFs.
- Do not change parser routing, extraction prompts, gold labels, or source
  fixture labels.
- Do not change runtime, model, GPU, service, schema, migration, or Cockpit UI
  files.
- Do not post GitHub comments, close issues, relabel, assign, or edit issue
  bodies.
- Do not perform unrelated cleanup, stash, reset, delete, merge, rebase, or
  branch cleanup operations.

## Required Behavior

- Reconcile the prior #96 approval packet against current repo evidence.
- Mark already-submitted BHP and PLS outcomes from the stopped canary retry.
- Exclude PLS and SFR advisory-only filings from the future primary candidate
  list under the current advisory-selection policy.
- Carry forward only unsubmitted, non-advisory primary candidates from the
  prior packet when current source paths still exist.
- Require immediate future checks for live terminal state, queue ownership,
  source-path existence, runtime loaded code, GPU process guard, and API health
  before any approved run.
- Require the exact approval string before any future canary execution.
- Preserve #97/#98/#99 boundaries: payload scorecard actuals after extraction,
  metric contract parity before interpreting unsupported families, and source
  asset reviewability as separate from correctness.
- State that the packet does not authorize broad backfill or canonical write
  promotion.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md --repo-root .`
- JSON validation for generated report artifacts.
- CSV shape sanity check for `canary_candidates.csv`.
- Raw PDF/source-data staging check.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md --repo-root .`
- Code-reviewer pass over the report-only diff.
- `python3 scripts/agent_job_registry.py release extraction_third_canary_approval_packet_refresh_v1_20260529 --repo-root .`
- Final registry read-only check and git status.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, registry status, files changed,
validation run with exact results, refreshed candidate list, excluded stale
candidate decisions, exact approval string required before the future run,
confirmation that no third canary/backfill/datastore/source/runtime mutation
ran, remaining blockers before full accurate extraction graduation, and final
git status.
