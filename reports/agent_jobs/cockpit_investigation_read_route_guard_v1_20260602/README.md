# Cockpit Investigation Read Route Guard

## Scope

- Issue: GitHub #222, "[Reporting] Gate Codex investigation read route before exposing output tails"
- Lane: Reporting
- Worktree: `/home/l4nd0/tenn-cockpit-investigation-read-route-guard-v1-20260602`
- Branch: `safe/cockpit-investigation-read-route-guard-v1-20260602`
- Mode: SAFE EXTENSION

## Patch Summary

- Added a server-side read guard to `GET /api/cockpit/feedback/flags/{reportId}/investigation`.
- The guard now rejects missing or wrong `X-Cockpit-Control-Intent: read-codex-investigation` before awaiting params, validating report IDs, resolving report paths, or reading investigation/log artifacts.
- Preserved accepted response shape for authorized loopback/same-origin reads.
- Kept `/cockpit-local/.../investigation` aligned through the existing re-export.
- Added the matching read-intent header to the Cockpit chat Codex investigation polling fetch so the current operator flow can still poll status.

## Overlap Evidence

- Shared registry check showed one active unrelated Evaluation job:
  `extraction_residual_candidate_filtering_bounded_sample_rerun_v1_20260602`.
- Registry `check-overlap` for this task returned `ok: true` with no issues.
- Open PR exact-file overlap check found no open PR touching:
  - `cockpit-ui/app/api/cockpit/feedback/flags/[reportId]/investigation/route.ts`
  - `cockpit-ui/lib/codex-investigation-route.test.ts`
  - `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
  - `cockpit-ui/lib/codex-investigation.ts`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_investigation_read_route_guard_v1_20260602.md --write-report` passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_investigation_read_route_guard_v1_20260602.md` passed.
- Red test before patch: `corepack pnpm --dir cockpit-ui exec vitest run lib/codex-investigation-route.test.ts` failed 3 guard tests as expected.
- Green test after patch: `corepack pnpm --dir cockpit-ui exec vitest run lib/codex-investigation-route.test.ts` passed, 6 tests.
- `corepack pnpm --dir cockpit-ui exec eslint 'app/api/cockpit/feedback/flags/[reportId]/investigation/route.ts' 'lib/codex-investigation-route.test.ts' 'components/cockpit/chat/chat-screen.tsx'` passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false` passed.
- `git diff --check` passed.

## Files Intentionally Not Touched

- Codex deploy/spawn route remains separate issue #215.
- Feedback UI hiding and repair-control visibility remains separate issue #108.
- Backend query orchestration, extraction, financial truth, memory, Qdrant, parser code, and runtime/GPU config were not changed.

## Remaining Follow-Up

- #215 still needs a deploy/spawn-side operator guard.
- This change does not claim to redact output tails; it gates read access before tails are exposed.
