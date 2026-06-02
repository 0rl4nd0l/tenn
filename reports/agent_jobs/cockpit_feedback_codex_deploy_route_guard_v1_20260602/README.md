# Cockpit Feedback Codex Deploy Route Guard

## Summary

Issue: #215
Branch: `safe/cockpit-feedback-codex-deploy-route-guard-v1-20260602`
Base: stacked on PR #248 branch `safe/cockpit-investigation-read-route-guard-v1-20260602`
Lane: Reporting
Mode: safe extension

The deploy route for flagged-report Codex investigations now rejects requests before report-id validation, local path resolution, backend flag refresh, launcher logging, or `spawn()` unless the request is loopback, same-origin, and carries `X-Cockpit-Control-Intent: deploy-codex-investigation`.

The `/cockpit-local/.../deploy` alias remains aligned through the existing re-export. The Cockpit chat deploy caller now sends the matching deploy-intent header. No live deploy, live investigator, backend query orchestration, extraction, memory, Qdrant, parser, runtime/GPU config, or financial-truth surfaces were changed.

## Overlap Evidence

- Shared registry check before claim: no active overlapping jobs.
- Open PR overlap: PR #248 touches `cockpit-ui/lib/codex-investigation-route.test.ts` and `cockpit-ui/components/cockpit/chat/chat-screen.tsx`; this work is intentionally stacked on #248 to avoid a competing same-file branch.
- Active job claim: `cockpit_feedback_codex_deploy_route_guard_v1_20260602` claimed in the shared registry for this isolated worktree.

## Validation

Commands run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_feedback_codex_deploy_route_guard_v1_20260602.md` - pass
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_feedback_codex_deploy_route_guard_v1_20260602.md --repo-root .` - pass
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_feedback_codex_deploy_route_guard_v1_20260602.md --repo-root .` - pass
- Red test run before implementation: `corepack pnpm --dir cockpit-ui exec vitest run lib/codex-investigation-route.test.ts` - failed 3 new deploy-guard tests as expected
- Green focused tests: `corepack pnpm --dir cockpit-ui exec vitest run lib/codex-investigation-route.test.ts` - 11 passed
- Targeted lint: `corepack pnpm --dir cockpit-ui exec eslint 'app/api/cockpit/feedback/flags/[reportId]/deploy/route.ts' 'components/cockpit/chat/chat-screen.tsx' 'lib/codex-investigation-route.test.ts'` - pass
- TypeScript: `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false` - pass
- `git diff --check` - pass

## Files Intentionally Not Touched

- Backend API routes and services
- Extraction and parser files
- Memory, Qdrant, DB, news, and financial-truth files
- Runtime/model/GPU/service configuration
- #108 normal-user UI visibility surfaces
- #121 broader action-control parity surfaces

## Remaining Blockers

This branch depends on PR #248 because it is stacked on the investigation read-route guard branch. Merge or rebase order should account for that dependency.
