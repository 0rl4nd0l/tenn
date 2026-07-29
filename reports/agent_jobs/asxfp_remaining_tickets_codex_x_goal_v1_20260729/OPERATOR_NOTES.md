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
- The first Codex X child run
  `20260729T122339Z-a68eb7b70a-de22f3` stopped before task-card validation,
  tests, or edits because the card called the underlying canonical commit the
  required worker `HEAD`. The actual launcher-pinned seed HEAD was
  `a68eb7b70a2a19bb39e15430ed856fb61e82701d`. The run produced no delta and
  consumed no RED/GREEN product attempt. The corrected identity contract
  distinguishes the canonical product base from the authorized orchestration
  seed and permits one equivalent retry.
- The equivalent implementer run
  `20260729T122958Z-f3bbcab50c-229d1c` used `gpt-5.6-sol`, verified the exact
  remote-pinned seed `f3bbcab50ce56a9769dfaae1ee0b8b52fc886865`,
  demonstrated the synthetic failure directly, and produced a three-file
  delta with frozen binary diff SHA-256
  `832b9afc19e117aa7dfc198ea42eb586731984cd1969eea4e79326d3eb6de0d5`.
- The fresh independent reviewer run
  `20260729T123718Z-599ccdfaf0-bfedbc` reviewed immutable candidate
  `599ccdfaf083d3d8f5d44949c4809216b4525a9f` and returned `ACCEPT`: zero
  standards violations, zero specification blockers, and one non-blocking
  opportunity to add dedicated negative-path tests later. It made no tracked
  changes.
- Parent validation of the byte-identical accepted delta:
  - classifier suite: 26 passed;
  - fixture/contract/sidecar/schema suites: 42 passed;
  - related source-document classifier cases: 6 passed;
  - two run-multipass cases were unavailable because the disposable
    environment lacked the optional Docling module;
  - Ruff lint, Python compilation, task-card validation, task-card
    `check-diff`, and `git diff --check`: passed;
  - Ruff format check remained non-green on both unchanged baseline files and
    was not introduced by the candidate.
- The accepted product commit is
  `3fb10c95ce01ecf6e8e7d730ec15f4ed16cb92f1`, tree
  `41532f66e89c7a084e70770cb1b7441083442e6b`.
- No source PDF, protected corpus path, diagnostic artifact, extraction,
  runtime, service, database, queue, model, GPU, deployment, activation, or
  merge action was used.
- Draft PR `https://github.com/0rl4nd0l/tenn/pull/530` opened against
  `migration/clean-runtime-baseline-reconstruct-v1`. The attached waiter
  recorded stable `SUCCESS` for `lint-and-test` and `scan` at exact head
  `aaf2dd39ad6d243932e873a9124e5e14edcc6020`. The PR remains open and draft;
  no merge was attempted.
- Ticket 04 has reached its authorized draft-PR closeout. The durable goal
  advances to Ticket 05, subject to a fresh canonical/dependency check.
