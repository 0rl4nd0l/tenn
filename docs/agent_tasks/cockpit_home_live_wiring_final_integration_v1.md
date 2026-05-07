---
job_id: cockpit_home_live_wiring_final_integration_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_live_wiring_final_integration_v1.md
  - docs/agent_tasks/cockpit_home_bff_route_v1.md
  - docs/agent_tasks/cockpit_home_bff_route_v1_integration.md
  - docs/agent_tasks/cockpit_home_live_wiring_v1.md
  - docs/agent_tasks/cockpit_shell_sidebar_nested_button_fix_v1.md
  - reports/agent_jobs/cockpit_home_live_wiring_final_integration_v1/**
  - reports/agent_jobs/cockpit_home_bff_route_v1/**
  - reports/agent_jobs/cockpit_home_bff_route_v1_integration/**
  - reports/agent_jobs/cockpit_home_live_wiring_v1/**
  - reports/agent_jobs/cockpit_shell_sidebar_nested_button_fix_v1/**
  - cockpit-ui/app/api/cockpit/home/route.ts
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-contract.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
  - cockpit-ui/types/cockpit-home.ts
  - cockpit-ui/components/cockpit/home/contextual-assistant.tsx
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/components/cockpit/home/market-status-header.tsx
  - cockpit-ui/components/cockpit/home/source-detail-drawer.tsx
  - cockpit-ui/components/cockpit/cockpit-sidebar.tsx
  - cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx
approval_required: true
timeout_seconds: 2400
output_dir: reports/agent_jobs/cockpit_home_live_wiring_final_integration_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Integrate Cockpit Home live wiring and sidebar nested-button fix into a clean integration branch.

# Required preflight

Run:
- pwd
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_live_wiring_final_integration_v1.md
- python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_live_wiring_final_integration_v1.md --repo-root <current integration worktree>

Proceed only if overlap is clear.

# Integration

Integrate the Cockpit Home chain and sidebar fix using the safest method:
- fast-forward/merge from the sidebar-fix branch if it already contains the full chain, or
- cherry-pick the missing commits in order.

Hard stop if conflicts touch files outside allowed_files.

# Validation

From cockpit-ui/:
- pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts components/cockpit/cockpit-sidebar.test.tsx
- npx tsc --noEmit --pretty false
- pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-api.test.ts components/cockpit/home/home-page.tsx components/cockpit/home/market-status-header.tsx components/cockpit/home/source-detail-drawer.tsx components/cockpit/home/contextual-assistant.tsx components/cockpit/cockpit-sidebar.tsx components/cockpit/cockpit-sidebar.test.tsx

Browser validation:
- start Next dev server on a free port
- open /
- verify GET /api/cockpit/home returns 200
- verify Cockpit Home renders BFF-backed state
- verify no nested-button console error
- verify delete chat session control is visible and does not select session when clicked
- verify no legacy /chat or /api/chat request is introduced by Home/sidebar
- note any remaining Vercel analytics/layout hydration warning separately

From repo root:
- git diff --check
- python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_live_wiring_final_integration_v1.md

# Final report

Write:
reports/agent_jobs/cockpit_home_live_wiring_final_integration_v1/README.md

Include:
1. base branch/HEAD
2. integration branch/HEAD
3. exact commits included
4. files changed
5. validation results
6. browser validation result
7. remaining out-of-scope browser warnings
8. registry release status
9. whether final integration branch is clean
10. whether safe to merge/fast-forward into preserve from a clean checkout
11. Project Memory save recommendation

Do not merge into the dirty preserve worktree.
Do not commit unrelated files.
