# Validation

## Commands

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md`
  - Result: passed.
- `git diff --check`
  - Result: passed.
- `pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/chat-screen.test.tsx components/cockpit/cockpit-sidebar.test.tsx`
  - Result: blocked by missing local frontend dependency.
  - Output: `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL Command "vitest" not found`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md --repo-root .`
  - Result: passed. `disallowed_files: []`.
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - Result: passed.

## Environment Notes

- `cockpit-ui/package.json` declares `vitest`, but neither `cockpit-ui/node_modules`
  nor root `node_modules` exists in this worktree.
- No dependency install was run because this job forbids package or lockfile
  mutation and the task card allows recording the missing Vitest blocker.

## Validation Status

DONE_WITH_RISK: containment and static checks passed, but the focused Vitest
tests could not run in the current local frontend environment.
