---
job_id: cockpit_shell_sidebar_nested_button_fix_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md
  - reports/agent_jobs/cockpit_shell_sidebar_nested_button_fix_v1/**
  - cockpit-ui/components/cockpit/cockpit-sidebar.tsx
  - cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_shell_sidebar_nested_button_fix_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Fix Cockpit sidebar nested-button hydration error.

Primary lane: Reporting

# Goal

Remove invalid nested `<button>` HTML in the Cockpit sidebar chat-session controls without changing Cockpit Home BFF behavior, chat routing, backend runtime code, or data stores.

# Context

Browser validation of Cockpit Home live wiring shows:
- `/api/cockpit/home` returns 200.
- Home live wiring works.
- Browser cleanliness is still blocked by a pre-existing shell/sidebar issue:
  - `<button> cannot be a descendant of <button>`
  - delete chat session Button appears nested inside SidebarMenuButton.

# Allowed work

Allowed:
- Edit `cockpit-ui/components/cockpit/cockpit-sidebar.tsx`.
- Add/update focused sidebar test if practical.
- Write report artifacts.

# Forbidden work

Do not:
- edit Cockpit Home BFF/live-wiring files
- edit backend runtime code
- edit legacy `/chat`
- touch marketplace/MCP/metric-coverage files
- mutate databases, Qdrant, news stores, memory stores, or production/local data
- change chat session deletion semantics except as needed to avoid nested button HTML
- commit without explicit later instruction

# Required preflight

Run:
- pwd
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md
- python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md --repo-root <current worktree root>

Proceed only if overlap is clear.

# Fix requirements

Find the chat-session row that nests a delete `Button` inside `SidebarMenuButton`.

Fix by changing structure so there is no button-inside-button, for example:
- make the parent row a non-button container and keep separate controls, or
- render the delete control as a non-nested sibling button, or
- use `asChild`/non-button element only if accessible and valid.

Preserve:
- chat session selection
- delete chat session action
- keyboard accessibility
- visual layout

# Validation

From `cockpit-ui/`:
- run focused sidebar test if present/added
- run targeted eslint on `components/cockpit/cockpit-sidebar.tsx`
- run `npx tsc --noEmit --pretty false`

Browser validation:
- start Next dev server on a free port
- open `/`
- verify no nested-button console error
- verify `/api/cockpit/home` still returns 200
- verify chat session delete control still appears and does not trigger session selection unintentionally
- verify no legacy `/chat` or direct datastore requests are introduced

From repo root:
- git diff --check
- python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md

# Final report

Write:
reports/agent_jobs/cockpit_shell_sidebar_nested_button_fix_v1/README.md

Include:
1. Branch / HEAD / worktree / dirty status
2. Task card and registry status
3. Root cause
4. Files changed
5. Accessibility/interaction behavior
6. Browser validation result
7. Tests run and exact results
8. Collision risk
9. DATA_MISSING
10. Whether commit is safe
