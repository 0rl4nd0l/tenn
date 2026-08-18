# PR #39 C01 Reconciliation Preservation

## Status

- Job: `pr39_c01_reconciliation_preservation_v1_20260527`
- Related C01 job: `pr39_backend_architecture_invariant_reconciliation_v1_20260527`
- Issue: #105 remains open.
- PR: #39 remains open, draft, and not merge-ready.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Local HEAD before preservation: `2d9067f0c5b75025886ab782f993bcb532492b48`
- PR #39 GitHub head inspected: `8635833b7d7359ed55daf0495eb49c5457bab91d`

## Decision

The C01 reconciliation diff is now preserve-ready in this worktree. The current
visible dirty set is fully inside the preservation task-card allowlist, so an
extra isolated worktree is not required.

The preservation remains local-only:

- no push;
- no PR #39 update;
- no issue #105 closeout;
- no DB, Qdrant, news, memory, runtime, parser, prompt, gold-label, or GPU
  mutation.

## What Is Being Preserved

- The C01 task card.
- The preservation task card.
- Architecture docs clarifying SQLite and random ID boundaries.
- Focused invariant tests that encode the clarified contract.
- Historical C01 audit and validation artifacts.
- This preservation report bundle.

## Current Validation

Passed in the current turn:

- task-card validation for the preservation card;
- task-card validation for the C01 card;
- focused invariant tests: `13 passed in 5.37s`;
- targeted Ruff check;
- targeted Ruff format check;
- `git diff --check`;
- preservation task-card `check-diff`.

Pending until after commit:

- commit hash recorded in this report bundle;
- final registry release;
- final clean/expected git status.

## PR #39 Impact

This preserves the local C01 fix but does not make PR #39 green. The PR still
needs either a push/rerun approval path or follow-up remediation for remaining
failure clusters beyond C01.

## Next Safe Step

After this local preservation commit, the next bounded child task should be C02:
Cockpit chat/session `llm_client` contract drift, unless the operator first
approves a PR #39 update and CI rerun plan for C01.
