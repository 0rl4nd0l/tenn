# Decisions

## Accepted Policy

Policy: `RETAIN_UUIDV5_PHYSICAL_MAPPING`

Keep `document_id:chunk_index` as the canonical logical vector/chunk ID. Permit
deterministic UUIDv5 only as the physical Qdrant point ID at the backend adapter
or direct-script storage boundary.

## Stale Shot 1 Worktree

The prior Shot 1 worktree was stale against current canonical, so it was left
untouched. Shot 2 moved to a fresh current-base sibling worktree.

## Direct ASX Embed Script

`financial-engine_v2/scripts/embed_docs_to_qdrant.py` writes directly to Qdrant
without `upsert_points()`. It was added to the task-card allowlist and updated
to include `logical_vector_id` in payloads. The script was not executed.

## GitHub

Initial Shot 2 implementation performed no PR or issue mutation because
`github_mutation_allowed: false`.

Follow-up owner approval on 2026-06-29 permits:

- rebasing branch `safe/issue266-qdrant-vector-id-contract-shot2-v1-20260629`
  onto current canonical `origin/migration/clean-runtime-baseline-reconstruct-v1`
  at `6c486d07743d3483d05fa163dc5c02fd66b68863`;
- rerunning focused validation;
- pushing the task branch;
- opening a draft PR.

No issue comments, issue closure, merge, force push, runtime/data mutation, or
live Qdrant proof are included in this approval.

Draft PR #473 was opened against
`migration/clean-runtime-baseline-reconstruct-v1`:
`https://github.com/0rl4nd0l/tenn/pull/473`.

The PR remains draft. No ready-for-review, merge, issue comment, or issue close
action was taken.
