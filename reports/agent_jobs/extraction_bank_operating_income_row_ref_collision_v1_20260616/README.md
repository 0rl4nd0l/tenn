# Bank Operating Income Row Ref Collision Integration

Status: `DONE_WITH_RISK`

This packet tracks integration of stranded commit
`c053cd77250c470af0af7af84764a7dd92fa9d36` into current canonical base through
a new PR.

## Preflight

- PR #362 live state: `MERGED`.
- PR #362 merge commit: `f838aeef58fc3573f8a5b47a704e44c26a005cf0`.
- Current canonical base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1` at `f838aeef`.
- Stranded fix commit: `c053cd77`.
- Containment: `c053cd77` is not contained in current canonical base.
- Source branch: `c053cd77` is contained in
  `origin/safe/extraction-lbl-income-row-ref-repair-v1-20260616`.
- New worktree:
  `/home/l4nd0/tenn-bank-operating-income-row-ref-collision-v1-20260616`.
- New branch:
  `safe/extraction-bank-operating-income-row-ref-collision-v1-20260616`.
- Registry read-only: no active jobs.
- Task ledger: `DATA_MISSING` for both live and committed ledger files.
- Duplicate fallback: only merged PR #362 and the old stranded branch matched.

## Decision

`PROCEED_AS_NEW_INTEGRATION_PR`.

The review fix is real, stranded, and not yet canonical. A new integration PR is
the smallest safe path.

## Implementation

Applied only the functional fix and focused regression from stranded commit
`c053cd77`:

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
  - Exact bank row labels `netinterestincome` and `totaloperatingincome` now map
    to `revenue` before the generic EBIT substring branch.
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
  - Added regression proving `Total operating income` binds `revenue`,
    `Profit before income tax` binds `ebit`, and `revenue` does not remain
    unbound.

No old PR #362 report files were changed in this integration branch; this packet
is the focused canonical integration record.

## Validation

- Task-card validate: passed.
- RED test: failed as expected on canonical base. Failure showed `ebit` bound to
  `Total operating income` and `revenue` unbound.
- GREEN focused tests: `2 passed`.
- `py_compile`: passed.
- `ruff`: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed.
- Changed-path/boundary guard: only approved source, test, task-card, and
  report files changed; no count-24 packet touched.

## Unsafe Actions Avoided

No count-24/count-32, broad extraction, random sample, backfill, canonical write,
DB/Qdrant/Redis/news/memory/source-PDF/prompt/gold/schema/runtime/model/GPU/
service mutation, branch deletion, worktree removal, or PR merge action.
