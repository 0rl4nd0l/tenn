# Cockpit Shell Sidebar Nested Button Fix v1

## 1. Branch / HEAD / worktree / dirty status

- Agent: Codex
- Branch: `codex/cockpit-shell-sidebar-nested-button-fix-v1`
- HEAD: `bae8b8fea5b3`
- Worktree: `/mnt/sdb2/home/l4nd0/tenn-cockpit-shell-sidebar-nested-button-fix-v1`
- Dirty status after implementation: allowed task files only:
  - `M cockpit-ui/components/cockpit/cockpit-sidebar.tsx`
  - `?? cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx`
  - `?? docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md`
- Note: the original preserve worktree and the live-wiring worktree both had unrelated dirty files outside this task card, so the fix was made in a fresh isolated worktree from `safe/cockpit-home-live-wiring-v1`.

## 2. Task card and registry status

- Task card created: `docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md`: ok, no issues.
- Shared registry preflight in isolated worktree:
  - `list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`: no active jobs before claim.
  - `check-overlap ... --repo-root /mnt/sdb2/home/l4nd0/tenn-cockpit-shell-sidebar-nested-button-fix-v1`: ok, no issues.
- Registry claim: succeeded for `cockpit_shell_sidebar_nested_button_fix_v1`.
- Registry release: succeeded after validation; shared registry active job list is empty.

## 3. Root cause

`CockpitSidebar` rendered each chat session as a `SidebarMenuButton`, which defaults to a real `<button>`. The delete chat session control was a nested `Button` inside that parent button, producing invalid HTML and the browser console error:

- `<button> cannot be a descendant of <button>`
- `<button> cannot contain a nested <button>`

## 4. Files changed

- `cockpit-ui/components/cockpit/cockpit-sidebar.tsx`
- `cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx`
- `docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md`
- `reports/agent_jobs/cockpit_shell_sidebar_nested_button_fix_v1/README.md`

## 5. Accessibility / interaction behavior

- The session selector remains a `SidebarMenuButton`.
- The delete control is now a sibling `SidebarMenuAction`, not a child of the session button.
- The delete action keeps keyboard/button semantics and an explicit accessible label: `Delete chat session: <title>`.
- Delete click handling still calls the existing delete handler and stops propagation, so it does not select the chat session.
- Existing hover/focus reveal behavior is preserved through the sidebar menu action pattern.

## 6. Browser validation result

Validated against a local Next dev server on `http://localhost:3019`.

- Real `GET /api/cockpit/home`: `200`.
- Browser-rendered delete control visible: yes.
- Delete request was mocked in Playwright to avoid backend/data-store mutation.
- Mocked delete count: `1`.
- Active session before delete: `data-active="true"`.
- Active session after delete: `data-active="true"`.
- Delete target before delete: `data-active="false"`.
- Delete target after delete: `data-active="false"`.
- Session button contained nested `<button>` before click: false.
- Session button contained delete action before click: false.
- Nested-button console errors: none.
- Page errors: none.
- Legacy `/chat` or `/api/chat` requests: none.
- Direct datastore-like browser requests: none.
- Residual unrelated browser console message: React dev hydration attribute warning on root HTML style, not a nested-button warning.

## 7. Tests run and exact results

- `pnpm install --frozen-lockfile --offline`: completed, lockfile unchanged; created ignored local `node_modules` for isolated worktree validation.
- `pnpm test components/cockpit/cockpit-sidebar.test.tsx`: `1 passed (1)`.
- `pnpm exec eslint components/cockpit/cockpit-sidebar.tsx components/cockpit/cockpit-sidebar.test.tsx`: exit 0.
- `npx tsc --noEmit --pretty false`: exit 0.
- `curl -sS -o /tmp/cockpit_home_3019.json -w '%{http_code}' http://127.0.0.1:3019/api/cockpit/home`: `200`.
- `git diff --check`: exit 0.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md`: ok after reverting generated `cockpit-ui/next-env.d.ts`.

## 8. Collision risk

- Expected collision risk: MEDIUM.
- Actual implementation risk: MEDIUM due Reporting lane UI change in a live multi-worktree repo.
- Contested surfaces touched: none.
- Risk reduction: isolated branch/worktree, clean task-card overlap, scoped edit to allowed sidebar/test/report files only.

## 9. DATA_MISSING

- Real chat-session deletion against the live backend was not performed because the task forbids data-store mutation. Browser click validation used a mocked same-origin DELETE response.
- The unrelated React dev hydration attribute warning was observed but not investigated because it is outside this task card and does not mention nested button HTML.

## 10. Whether commit is safe

Commit is safe after explicit user instruction. No commit was made.
