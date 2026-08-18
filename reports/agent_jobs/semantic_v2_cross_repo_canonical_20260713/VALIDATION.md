# Validation

- Task-card validation: passed; computed fingerprint
  `2379538a7a034c661a6e2af90d5615fc1622e5be57699d88ecb3b0e80e84a758`.
- V2 portable preflight before substantive edits:
  `semantic_control_status=ALLOW_NEW_SCOPE`,
  `decision_ledger_status=PASS`, `final_decision=pass`.
- RED proof: the new cross-repository test failed because canonical identity
  remained Tenn-specific before the guard patch.
- Focused canonical/path tests: 4 passed.
- Full portable guard unittest suite: 40 passed. Published feature refs cannot
  become canonical; Tenn fallback, remote symbolic default, Greyhound
  `origin/master`, and a non-`origin` remote are covered. The stable
  `~/tenn-semantic-anti-loop-v2-canonical` root outranks arbitrary alphabetic
  `~/tenn-*` worktrees and discovery falls through when it is absent.
- Focused hook suite: 76 passed. Automatic and explicit env/marker V2 selection
  blocks a missing outcome, post-claim card/version drift, partial or fully
  stripped V2 identity, corrupt unscoped registry JSON, stale-named invalid
  records, unscopable worktrees, and ambiguity. The stripped-record proof runs
  for Stop and BeforeTool, including combined stripped identity plus missing or
  invalid worktree. It reads card bytes once for both version detection and
  hash verification, and leaves unchanged, missing-card, or invalid-worktree
  V1 records silent. A missing or corrupt active-record card hash is treated as
  additional corruption and cannot erase V2 authority declared by the card.
  A matching outcome/decision is still accepted.
- Contract, hook, registry, board, decision-ledger, and task-ledger pytest set:
  251 passed, 13 subtests passed; one existing unknown-pytest-option warning.
- Ruff over the changed Python files: passed.
- `py_compile` over the changed Python files: passed.
- `git diff --check`: passed.
- `PUBLISH` is explicitly declared for one bounded follow-up commit, push, PR,
  and merge after final review; no deployment or runtime activation is allowed.
- Actionable cross-repository review findings were repaired. The final
  independent adversarial review was `CLEAN` with no remaining critical,
  warning, or suggestion findings.
