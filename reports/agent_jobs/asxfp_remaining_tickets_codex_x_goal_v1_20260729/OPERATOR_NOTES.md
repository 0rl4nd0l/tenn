# Operator notes

## 2026-07-29

- Verified live canonical
  `migration/clean-runtime-baseline-reconstruct-v1` at
  `b01885d6cd55242339662e91d18141aeb725f089`.
- Preserved the unrelated clean checkout
  `/home/l4nd0/tenn` on
  `fix/llama-router-fail-closed-v1-20260726`.
- Verified issues 73, 96, and 97 remain open; issue 286 is closed.
- Verified Codex X exact-ref network-read dry-run. The launcher pins the remote
  SHA, hands the child to an offline isolated worktree, removes the remote
  before launch, and disallows publication from the child.
- Classified the Ticket 04 residual as `NEW_FAILURE_CLASS`, with a synthetic
  cross-page regression as the permanent gate.
- The 172-page anchor-absent half-year document is outside this narrow repair
  and remains `DATA_MISSING`.
