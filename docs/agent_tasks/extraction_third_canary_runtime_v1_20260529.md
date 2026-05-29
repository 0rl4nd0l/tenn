---
job_id: extraction_third_canary_runtime_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Query Orchestration
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_third_canary_runtime_v1_20260529.md
  - reports/agent_jobs/extraction_third_canary_runtime_v1_20260529/README.md
  - reports/agent_jobs/extraction_third_canary_runtime_v1_20260529/status.json
  - reports/agent_jobs/extraction_third_canary_runtime_v1_20260529/canary_results.json
  - reports/agent_jobs/extraction_third_canary_runtime_v1_20260529/canary_actual_payloads.json
  - reports/agent_jobs/extraction_third_canary_runtime_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: true
allow_unapproved_safe_extension: false
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_third_canary_runtime_v1_20260529
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User replied exactly: APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529"
approval_packet: reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/canary_approval_packet.json
---

# Extraction Third Canary Runtime V1

## Objective

Run the approved third #96 extraction canary for exactly the seven document IDs
from `extraction_third_canary_approval_packet_refresh_v1_20260529`, one
document at a time, through the backend-owned single-document route.

## Scope

- Primary lane: Financial Truth.
- Supporting lanes: Query Orchestration, Evaluation, Provenance.
- Mode: APPROVAL-GATED BOUNDED RUNTIME CANARY.
- Related issue: #96.
- Approval phrase received:
  `APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529`

## Contract Check

Target system layers: Extraction and Storage through the canonical backend API;
Evaluation/Provenance for post-run artifacts.

Relevant contract rules: backend is sole authority; extraction must only use
explicit source values; failures and ambiguity must fail visibly; no fallback,
parallel pipeline, parser-route mutation, prompt mutation, direct SQL mutation,
or canonical-truth promotion is introduced.

What must not change: source PDFs, parser routing, extraction prompts, gold
labels, schemas/migrations, runtime/model/GPU/service config, Cockpit UI,
GitHub issue state, direct DB/Qdrant writes, broad backfill behavior, or any
unapproved document.

Why safe: execution is limited to the existing
`POST /api/process/document/{document_id}` backend route, exactly seven
approved document IDs, one at a time, with abort gates before and during the run.

GPU process check required: yes. Run `scripts/gpu_process_guard.sh --check`
before the first extraction POST and stop if it exits non-zero.

## Approved Document IDs

1. AAU `508fc892-ae88-45ec-981f-cd9e124c8375`
2. ATM `96e9aabd-44dc-4c2c-be8c-74248a0a9025`
3. AM5 `aacc4c29-3089-48cf-8b82-8004134f9387`
4. AQX `0ed0104f-f29a-4068-8ff7-370f14fead98`
5. CRS `b43a16fb-7660-4bf7-96ab-0db641cd4032`
6. CLV `da9f9ea5-6596-464f-af14-5acf12f9b050`
7. CTM `035c6758-7aed-41a6-9e84-ad154125d431`

## Required Preflight

- Confirm repo path, branch, HEAD, upstream, and dirty state.
- Preserve unrelated active audit work in the baseline checkout.
- Validate this task card.
- Check registry overlap and claim this task card.
- Confirm the active Query Orchestration audit job does not overlap this
  task's files or runtime scope.
- Confirm approval packet exists and includes exactly the seven approved IDs.
- Confirm every source path exists immediately before execution.
- Confirm each document is not queued/running/orphaned if that status is
  available.
- Confirm backend `/api/health` is healthy.
- Confirm API key is available without printing it.
- Run `scripts/gpu_process_guard.sh --check`.
- Confirm live runtime loaded-code evidence or record `DATA_MISSING` if
  container/process evidence is unavailable.

## Execution Rules

- Use only `POST /api/process/document/{document_id}`.
- Submit one document at a time in approved order.
- Poll each run until terminal status before submitting the next document.
- Stop immediately on the first failed hard gate, failed extraction, queue
  orphan, source side effect, unexpected datastore effect, or runtime
  degradation.
- Do not run `/process/ticker`, broad backfill, direct Celery enqueue, direct
  SQL mutation, or any unapproved route.

## Forbidden

- Processing any document outside the approved seven IDs.
- Broad extraction/backfill.
- Direct SQL mutation.
- Qdrant/news/memory/canonical truth mutation outside the approved route's
  normal effects.
- Source PDF edits, moves, copies, deletes, or commits.
- Parser routing, extraction prompt, gold-label, schema, runtime, model, GPU,
  service, or Cockpit UI changes.
- GitHub comments, issue closure, relabeling, assignment, milestone changes, or
  issue body edits.
- Unrelated cleanup, stash, reset, delete, merge, rebase, or branch cleanup.

## Post-Run Audit

- Record per-document run ID, task ID, status, error, elapsed time, and result.
- Record extraction-run rows created for approved documents only.
- Record financial rows and metrics created for approved documents only.
- Record Qdrant point deltas for approved document IDs if measurable.
- Record risk-note, source-sidecar, news/memory, thesis-alert, and broad-queue
  side effects if measurable.
- Write `canary_actual_payloads.json` for #97 scorecard follow-up when actual
  extracted payloads are available.
- Keep #97 payload correctness, #98 metric contract parity, and #99 source
  reviewability as separate review gates.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_third_canary_runtime_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_third_canary_runtime_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_third_canary_runtime_v1_20260529.md --repo-root .`
- JSON validation for generated artifacts.
- Raw PDF/source-data staging check.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_third_canary_runtime_v1_20260529.md --repo-root .`
- Code-reviewer pass over report artifacts.
- Registry release and final list-active.
- Final git status.

## Final Report Requirements

Report approval source, branch, HEAD, worktree, task card path, registry status,
runtime preflight results, documents submitted, run IDs, per-document outcomes,
side-effect audit, generated artifacts, validation results, explicit statement
that no broad backfill/unapproved mutation ran, remaining blockers before full
accurate extraction graduation, and final git status.
