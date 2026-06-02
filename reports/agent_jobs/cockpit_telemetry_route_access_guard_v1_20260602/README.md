# Cockpit Telemetry Route Access Guard

## Summary

Implemented issue #223 in Reporting lane on isolated branch `safe/cockpit-telemetry-route-access-guard-v1-20260602`, stacked on PR #264.

- Added a small Next.js BFF helper that requires a configured Cockpit API key before sensitive telemetry routes run local probes.
- Gated `/api/cockpit/metrics/host`, `/api/cockpit/metrics/gpu`, and `/api/cockpit/health` before `df`, `ps`, `nvidia-smi`, OS probes, or backend health reads execute.
- Added a browser header helper and wired Cockpit health, Host Activity, and GPU Activity fetches to send the configured operator key.
- Preserved #218 command redaction behavior and added authenticated tests that assert redaction remains active.

## Scope And Contract

- Lane: Reporting
- Target layer: Client / Next.js BFF diagnostics
- Execution mode: SAFE EXTENSION
- Contested surfaces touched: `cockpit-ui/app/api/cockpit/health/route.ts`, `cockpit-ui/app/api/cockpit/metrics/gpu/route.ts`, `cockpit-ui/app/api/cockpit/metrics/host/route.ts`, `cockpit-ui/lib/api-client.ts`, Host/GPU dialog fetch wiring
- Collision risk: MEDIUM due stacked Cockpit UI telemetry PRs, with no unresolved active-job overlap
- GPU process check required: no; this task does not spawn, restart, or depend on llama-server

Relevant contract evidence:
- `docs/architecture/SYSTEM_CONTRACT.md` keeps Cockpit as client/orchestration only.
- `docs/architecture/21_cockpit_client_contract.md` treats Next.js BFF routes as presentation/aggregation surfaces and documents `X-API-Key`.
- `docs/architecture/13_security_and_secrets.md` prohibits exposing or committing real keys.

## Issue And Overlap Evidence

- `gh issue view 223 --repo 0rl4nd0l/tenn` returned OPEN with acceptance criteria for host/GPU/health telemetry access gating.
- `python3 scripts/agent_job_registry.py list-active` showed this job claimed in the isolated worktree plus one unrelated extraction/Evaluation job in the shared checkout.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_telemetry_route_access_guard_v1_20260602.md` returned `ok: true`, `issues: []`.
- `gh pr list --repo 0rl4nd0l/tenn --state all --search "cockpit telemetry route access guard"` returned no duplicate PRs.
- `gh issue list --repo 0rl4nd0l/tenn --state all --search "cockpit telemetry route access guard"` returned #223 plus adjacent route-gating follow-ups (#230, #238, #243), not a duplicate for this task.
- PR #264 is OPEN, mergeable, and green; this branch is stacked on it to compose with process-command redaction.
- PR #178 is OPEN, mergeable, and green; #264 is stacked on it.
- PR #197 is OPEN, mergeable, and green; it touches GPU telemetry UI and remains a rebase/integration dependency to watch.

## Validation

Commands run from `cockpit-ui/` unless noted:

- `node_modules/.bin/vitest run lib/cockpit-api-headers.test.ts lib/telemetry-route-access-guard.test.ts`
  Result: PASS, 2 files, 10 tests.
- `node_modules/.bin/eslint 'app/api/cockpit/metrics/gpu/route.ts' 'app/api/cockpit/metrics/host/route.ts' 'app/api/cockpit/health/route.ts' 'lib/cockpit-bff-auth.ts' 'lib/cockpit-api-headers.ts' 'lib/cockpit-api-headers.test.ts' 'lib/telemetry-route-access-guard.test.ts' 'lib/api-client.ts' 'components/cockpit/gpu-activity-dialog.tsx' 'components/cockpit/host-activity-dialog.tsx'`
  Result: PASS.
- `node_modules/.bin/tsc --noEmit --pretty false`
  Result: PASS.
- Code-reviewer pass over modified and added files: no critical issues after fixing browser stored-key support.

## Files Intentionally Not Touched

- `financial-engine_v2/backend/**`
- `financial-engine_v2/cockpit/**`
- extraction, parser, prompt, gold-label, Qdrant, database, memory, runtime/model/GPU service configuration, and production data surfaces
- unrelated shared checkout dirt from the active extraction/Evaluation job

## Remaining Blockers Or Follow-Up

- This PR remains stacked on PR #264, which is stacked on PR #178; merge order should preserve that chain.
- PR #197 touches related GPU telemetry UI and may require a later rebase conflict check.
- Adjacent unauthenticated route-gating follow-ups remain tracked separately in #230, #238, and #243.
