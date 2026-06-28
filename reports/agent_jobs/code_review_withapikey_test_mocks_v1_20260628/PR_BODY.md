## Summary

- Add missing `withApiKey` exports to the ChatScreen and CockpitSidebar
  `@/lib/api-client` component-test mocks.
- Record the tiny code-review follow-up task card and validation report.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`

Blocked locally:

- `pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/chat-screen.test.tsx components/cockpit/cockpit-sidebar.test.tsx`
  failed because `vitest` is not installed in this worktree.

## Scope

No runtime, backend, extraction, data, package, or lockfile changes.
