# Post-PR299 Broad Accuracy Push

Lane:
Financial Truth

Branch:
safe/extraction-post-pr299-broad-accuracy-push-v1-20260606

Worktree:
/home/l4nd0/tenn-post-pr299-broad-accuracy-push-v1-20260606

Execution mode:
LONG-RUNNING SAFE PROGRESS / AUDIT FIRST / SAFE EXTENSION / BOUNDED VALIDATION

Intended files:
Parent and child task cards, scoped report artifacts, deterministic extraction
source-classification code/tests, candidate/scorecard taxonomy docs, and the
broad validation harness only if required for taxonomy consistency.

Contested surfaces touched:
`financial-engine_v2/backend/app/services/multipass_extraction.py` is a
Financial Truth surface. No edit has been made yet.

Collision risk:
MEDIUM/HIGH by task type, mitigated by isolated clean worktree and exact
allowed files.

Decision:
proceed with Phase 1 only after task-card validation.

## Objective

Push Tenn extraction closer to broad accuracy after PR #299 by completing the
next safe sequence: candidate-exclusion taxonomy, bounded count-16 validation,
and at most one narrow follow-up repair if evidence supports it.

## Current State

RUNNING.

## Constraints And Unsafe Actions

Forbidden actions include broad backfill, full ticker-universe extraction,
count-24/count-32, production DB writes, direct SQL mutation, Qdrant/news/memory
mutation, source PDF edits, prompt/gold-label/runtime/schema changes, service
restarts beyond minimal bounded validation readiness, broad fuzzy exclusions,
unrelated cleanup, and dirty NVMe parent-batch merge.

## Evidence Used

- Isolated worktree created from `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- HEAD in isolated worktree: `9436d1d32de0da5423b8edcfc7efc883ccac3fd6`.
- HEAD contains PR #299 merge commit by exact equality.
- Shared checkout was dirty and not based on PR #299, so it was not used for
  edits.
- Registry active-job state is `DATA_MISSING`: `list-active` has no safe
  read-only command path in this checkout.

## Files Touched

- `docs/agent_tasks/extraction_post_pr299_broad_accuracy_push_v1_20260606.md`
- `docs/agent_tasks/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606.md`
- `reports/agent_jobs/extraction_post_pr299_broad_accuracy_push_v1_20260606/README.md`

## Files Intentionally Not Touched

No source PDFs, DB/Qdrant/news/memory stores, prompts, gold labels, schemas,
runtime/model/GPU config, or services.

## Commands Run With Exit Status

- Preflight commands were run in the shared checkout and isolated worktree.
  Detailed validation command results will be added after task-card validation.

## Approvals Needed

No additional approval is needed for Phase 1 within the allowed files. Count-24
or count-32 would require explicit separate approval.

## Blocked Items And DATA_MISSING

- `DATA_MISSING`: safe registry active-job state, because `list-active` lacks a
  safe read-only path and the implementation references an undefined
  `args.read_only`.

## Validation Status

Pending.

## Raw Log Paths

None yet.

## Unsafe Actions Avoided

No sample, backfill, full ticker extraction, source-PDF mutation, datastore
mutation, service restart, stash, reset, cleanup, merge, rebase, or branch
deletion has run.

## Ignored Or Untracked Artifact Note

Report artifacts under `reports/agent_jobs/...` are expected to be ignored by
Git until force-added for commit.

## Remaining Risk

Phase 1 touches deterministic Financial Truth classification and must prove it
does not overblock valid financial-report candidates.

## Next Recommended Prompt

Continue Phase 1: audit the five false-positive source classes, implement only
narrow deterministic exclusions, and run focused validation.
