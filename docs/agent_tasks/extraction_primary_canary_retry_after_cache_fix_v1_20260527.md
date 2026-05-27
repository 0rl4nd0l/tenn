---
job_id: extraction_primary_canary_retry_after_cache_fix_v1_20260527
lane: Query Orchestration
supporting_lanes:
  - Financial Truth
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md
  - reports/agent_jobs/extraction_primary_canary_retry_after_cache_fix_v1_20260527/README.md
  - reports/agent_jobs/extraction_primary_canary_retry_after_cache_fix_v1_20260527/status.json
  - reports/agent_jobs/extraction_primary_canary_retry_after_cache_fix_v1_20260527/canary_results.json
  - reports/agent_jobs/extraction_primary_canary_retry_after_cache_fix_v1_20260527/diff-check.json
  - reports/agent_jobs/extraction_primary_canary_retry_after_cache_fix_v1_20260527/github_issue_96_comment.md
allowed_repo_files:
  - docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md
  - reports/agent_jobs/extraction_primary_canary_retry_after_cache_fix_v1_20260527/**
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_primary_canary_retry_after_cache_fix_v1_20260527
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
github_mutation_allowed: issue_comment_only
related_issue: 96
operator_approval_source: "User goal request in Codex session 2026-05-27 for bounded retry after cache fix"
---

# Extraction Primary Canary Retry After Cache Fix

## Objective

Run a runtime-readiness check for the integrated PyMuPDF fallback cache fix, then
retry only the approved bounded issue #96 extraction canary if and only if the
live backend and worker runtime are proven to be running canonical commit
`06cb29067d1021ea89d7b93341653d5750babe92` or a descendant.

The user requested `mutation_mode: implementation`; the repo task-card
validator currently accepts only `audit_only`, `safe_extension`, or `blocked`.
This card therefore records `requested_mutation_mode: implementation` and uses
the validator-compatible bounded `safe_extension` mode.

## Scope

- Primary lane: Query Orchestration.
- Supporting lanes: Financial Truth, Evaluation, Provenance.
- Mode: RUNTIME READINESS + BOUNDED CANARY ONLY.
- Risk: HIGH for runtime/data mutation; proceed only within the approved canary
  scope.
- Related issue: #96.

## Contract Check

- Target system layers: Extraction and Storage through the canonical backend
  single-document API; Evaluation and Provenance report artifacts after the run.
- Relevant contract rules: backend remains sole authority; extraction must
  preserve explicit source data, fail visibly, and avoid inference,
  substitution, or fabrication; storage writes are allowed only through the
  existing approved route; vector IDs and source data boundaries must remain
  deterministic.
- What must not change: parser routing, extraction prompts, gold labels, source
  PDFs, schemas/migrations, canonical truth promotion, runtime/model/GPU config,
  Cockpit UI, broad backfill behavior, news/memory writes outside route behavior,
  and any unapproved document.
- Why safe: the retry is bounded to a previously approved primary canary
  allowlist, submits one document at a time through
  `POST /api/process/document/{document_id}`, and aborts before canary execution
  unless loaded runtime commit and cache-path readiness are proven.
- GPU process check required: yes before the first canary POST, because
  extraction may depend on the live LLM runtime.

## Approved Canary Route

- `POST /api/process/document/{document_id}`
- Only for approved canary document IDs.
- No broad backfill route.
- No batch route.
- No reprocessing beyond approved IDs.

## Approved Primary Canary Document IDs

Retry the same first two documents that previously failed:

- BHP: `2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7`
- PLS: `918f0b4a-563b-4e53-962a-82f43882d667`

Only if both now pass the cache-path blocker and complete safely, continue
through the remaining approved primary candidates from
`extraction_bounded_canary_approval_packet_v1_20260527`, up to 10 total:

- SFR: `789130bc-b2db-45b3-a8e0-46d8c71588f1`
- AAU: `508fc892-ae88-45ec-981f-cd9e124c8375`
- ATM: `96e9aabd-44dc-4c2c-be8c-74248a0a9025`
- AM5: `aacc4c29-3089-48cf-8b82-8004134f9387`
- AQX: `0ed0104f-f29a-4068-8ff7-370f14fead98`
- CRS: `b43a16fb-7660-4bf7-96ab-0db641cd4032`
- CLV: `da9f9ea5-6596-464f-af14-5acf12f9b050`
- CTM: `035c6758-7aed-41a6-9e84-ad154125d431`

## Required Preflight

1. Confirm repo path, branch, HEAD, and remote.
2. Run `git status --short --untracked-files=all`.
3. Run `git worktree list`.
4. Check registry/list-active.
5. Validate this task card.
6. Confirm canonical includes
   `06cb29067d1021ea89d7b93341653d5750babe92`.
7. Confirm the live backend/worker loaded code commit is `06cb2906` or a
   descendant.
8. If live runtime commit cannot be verified, stop before canary and report
   `DATA_MISSING`.
9. Confirm `/api/health` or equivalent runtime health.
10. Confirm source PDFs remain read-only inputs.
11. Confirm the approved canary candidate packet/report exists.
12. Confirm no active registry job overlaps extraction/runtime surfaces.

## Runtime Readiness Checks

- Identify backend process/container/worktree path.
- Confirm loaded git commit or image/build metadata.
- Confirm the PyMuPDF cache path resolves under
  `<settings.data_root>/reports/extraction_cache/docling_extract/`.
- Confirm no `*.pdf.pymupdf.json` sidecar will be written beside
  `/data/asx/docs` source PDFs.
- If readiness cannot be proven, stop and do not run canary.

## Canary Execution

- Submit BHP first and capture run ID, task ID, status, logs/error, emitted
  artifacts, and DB/Qdrant side effects.
- Submit PLS only if BHP does not show the same deterministic blocker.
- Continue to orders 3-10 only if BHP and PLS both pass the cache-path blocker
  and finish safely.

## Abort Gates

- Repeated deterministic parser/cache/source-write error.
- Source PDF sidecar write attempt.
- Unexpected DB/Qdrant/news/memory mutation.
- Runtime degradation.
- Queue orphaning.
- Any unapproved route use.
- Any need for broad extraction/backfill.
- Any service restart unless required to load canonical code and explicitly
  reported.

## Forbidden

- Broad extraction/backfill.
- Production DB writes outside the approved route's normal extraction-run
  effects.
- Direct SQL mutation.
- Qdrant/news/memory mutation outside whatever the approved route already does.
- Canonical truth promotion beyond approved route behavior.
- Parser routing changes.
- Extraction prompt changes.
- Gold-label mutation.
- Source PDF edits, moves, copies, deletes, or commits.
- Runtime/model/GPU config changes.
- Cockpit UI implementation.
- Schema migrations.
- Issue closure, relabeling, assignment, milestone changes, or issue body edits.
- Unrelated cleanup, stash, reset, delete, merge, rebase, or branch cleanup.

## Post-Run Audit

- List submitted documents only.
- List extraction_run rows created for submitted documents.
- Check financial rows created for submitted documents only.
- Check Qdrant points if the route writes any; report exact behavior.
- Confirm no risk notes, thesis alerts, news/memory writes, or broad queue jobs
  were created.
- Confirm no source PDFs were modified and no sidecar files were written beside
  them.
- Confirm cache artifacts were written only under the approved cache root.
- Compare outcomes against #97/#98/#99 gates: payload scorecard readiness,
  metric contract parity, and source asset reviewability.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md --repo-root .`
- JSON validation for generated reports.
- Raw PDF staging check.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md --repo-root .`
- Registry release and final list-active.
- Final `git status --short --untracked-files=all`.

## Final Report Requirements

- Runtime readiness verdict.
- Loaded runtime commit proof.
- Documents submitted.
- Run IDs.
- Per-document result.
- Whether the cache-path blocker is resolved.
- Extracted metric rows, if any.
- Abstain/quarantine outcomes, if any.
- Side-effect audit.
- Whether a second canary batch is safe to propose.
- Remaining `DATA_MISSING`.
- Statement that no broad backfill was run.
- Project Memory save recommendation.
- If GitHub auth allows, comment a concise update on #96 with the report path
  and remaining `DATA_MISSING`; do not close, relabel, assign, milestone, or
  edit the issue.
