# Validation

## Contract And Ledger

- V2 task-card validation: passed; fingerprint
  `583fb5953d20739245440776196b1a03d82cd161a6d4d9543cbbf13b5cf25779`.
- Decision-entry validation: passed before append.
- Tenn shared decision-ledger initialization: passed; created one empty
  append-only ledger under the existing shared registry lock.
- Repeated ledger validation: passed with zero entries before closeout append.

## Focused Tests

- Combined contract, hook, registry, board, decision-ledger, and task-ledger
  suite: 208 passed, 13 subtests passed; one existing pytest configuration
  warning for `asyncio_default_fixture_loop_scope`.
- Portable guard unittest suite: 34 passed.
- Ruff over all changed Python/control tests: passed.
- `py_compile` over changed production Python: passed.
- `git diff --check`: passed.

## Portable Proof

The repo-backed portable guard selected this V2-capable control-plane worktree,
reported `control_contract_status=V2`, `decision_ledger_status=PASS`,
`registry_status=PASS`, and `semantic_control_status=ALLOW_NEW_SCOPE`. It then
returned exit 3 because the intended task diff made the worktree
`DIRTY_RELATED_WORKTREE`; the allowed-file `check-diff` is the corresponding
post-edit gate.

## Local Gates

- final bounded post-fix code review: clean;
- task-card `check-diff`, `check-closeout`, and report-artifact checks: passed;
- exact run-bound ledger append: passed;
- Codex Stop hook with the matching task card and durable decision: passed;
- repeat preflight classified the exact fingerprint as `REUSED_COMPLETE`,
  set `report_write_permitted=false`, and returned the V2 hard-stop status;

## Pending Publication Checks

- exact GitHub PR head and checks;
- merge ancestry verification.
