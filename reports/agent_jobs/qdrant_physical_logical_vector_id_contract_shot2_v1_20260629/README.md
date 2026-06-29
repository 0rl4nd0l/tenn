# Qdrant Physical Versus Logical Vector ID Contract Shot 2

Issue: #266

Branch: `safe/issue266-qdrant-vector-id-contract-shot2-v1-20260629`

Draft PR: `https://github.com/0rl4nd0l/tenn/pull/473`

Worktree:
`/home/l4nd0/tenn-issue266-qdrant-vector-id-contract-shot2-v1-20260629`

## Summary

Implemented the approved `RETAIN_UUIDV5_PHYSICAL_MAPPING` policy.

The canonical logical vector ID remains `document_id:chunk_index` and is now
preserved in Qdrant payloads as `logical_vector_id`. The backend Qdrant adapter
keeps deterministic UUIDv5 physical point IDs for non-UUID logical IDs. Random
UUID vector/chunk IDs remain forbidden.

## Scope

Changed:

- Backend Qdrant adapter payload enrichment and ASX logical-ID guard.
- Pipeline and commentary staging payloads.
- Read-only Qdrant inspector interpretation.
- Architecture docs and focused tests.

Not changed:

- No live Qdrant, DB, Redis, news, memory, source PDF, gold label, service,
  runtime, model, GPU, or production data mutation.
- No rebuild, reindex, backfill, service restart, issue mutation,
  ready-for-review action, or merge.

Follow-up owner approvals permit rebasing this task branch onto current
canonical, rerunning focused validation, pushing/updating the branch, and
opening or maintaining draft PR #473.

## Result

result: DONE_WITH_RISK

Reason: implementation and focused validation passed, but no live Qdrant runtime
output was mutated or proven. This is code/docs/test completion only. Draft PR
#473 is open and was refreshed onto canonical `ca424a28` after final
merge-readiness verification found no code-level blockers but guard classified
the older PR branch as stale again. Ready-for-review and merge were not
performed.
