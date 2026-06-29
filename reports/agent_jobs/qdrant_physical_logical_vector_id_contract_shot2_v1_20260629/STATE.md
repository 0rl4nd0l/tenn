# State

status: rebased_pending_publish

result: DONE_WITH_RISK

## Evidence

- `gh issue view 266` on 2026-06-29 showed issue #266 open, unassigned, and
  ready.
- Current-base worktree guard passed on branch
  `safe/issue266-qdrant-vector-id-contract-shot2-v1-20260629`.
- Active registry was empty before claim.
- Owner approval was received as `proceed` after the Shot 1 recommendation to
  use `RETAIN_UUIDV5_PHYSICAL_MAPPING`.
- Follow-up owner approval was received as `proceed` after the guard blocked
  publication from a stale path and requested explicit approval to rebase onto
  current canonical, rerun focused validation, push the branch, and open a
  draft PR.
- Branch was rebased successfully onto
  `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `6c486d07743d3483d05fa163dc5c02fd66b68863`.

## Implementation

- Added `logical_vector_id` preservation for ASX document chunks and commentary
  staged chunks.
- Centralized deterministic UUIDv5 physical Qdrant point-ID coercion in
  `embeddings.py`.
- Added an `asx_docs` write guard that rejects point IDs that do not match
  `document_id:chunk_index`.
- Updated the read-only Qdrant inspector to distinguish logical ID mismatches
  from physical point-ID mismatches.
- Updated architecture docs and focused tests.

## Runtime Proof

No live runtime functionality was claimed.

result: DATA_MISSING

| Field | Required evidence |
| --- | --- |
| intended output | Future Qdrant writes preserve `logical_vector_id` and deterministic physical point IDs. |
| live output location | `DATA_MISSING`; no live Qdrant write/reindex was run. |
| pre-run max timestamp or count | `DATA_MISSING`; no live Qdrant baseline was captured. |
| post-run max timestamp or count | `DATA_MISSING`; no live Qdrant mutation was performed. |
| rows/files inserted or updated after run start | zero runtime rows/points; code/docs/report files only. |
| readiness/gate status | Focused local validation passed; live runtime readiness not proven. |
| exact command/query used | See `VALIDATION.md`; no live Qdrant query was required for this code/docs task. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | DATA_MISSING |
| remaining blocker | Live Qdrant/backfill proof would require separate runtime/data approval. |

## Unsafe Actions Avoided

- No production Qdrant or DB mutation.
- No live reindex/rebuild/backfill.
- No service restart.
- No issue comment, issue closure, merge, force push, live runtime write, or
  production data mutation.
