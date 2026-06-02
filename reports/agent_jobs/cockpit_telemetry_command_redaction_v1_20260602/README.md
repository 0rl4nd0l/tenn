# Cockpit Telemetry Command Redaction

## Summary

Issue: #218
Branch: `safe/cockpit-telemetry-command-redaction-v1-20260602`
Base: stacked on PR #178 branch `safe/cockpit-llama-gpu-primary-display-v1-20260601`
Lane: Reporting
Mode: safe extension

Cockpit telemetry command strings are now redacted before they leave the server-side BFF routes. The shared helper redacts secret-bearing CLI flags, environment assignments, and authorization headers while preserving useful process context such as command names, ports, non-secret args, PIDs, task labels, and resource metrics.

Applied routes:

- `GET /api/cockpit/metrics/gpu`
- `GET /api/cockpit/metrics/host`
- `GET /api/cockpit/health`

No live telemetry probe, runtime/model/GPU config change, backend query orchestration change, extraction change, memory/Qdrant/DB/news write, parser change, or financial-truth change was performed.

## Overlap Evidence

- Shared registry check before claim: no active jobs.
- Open PR overlap: PR #178 touches `cockpit-ui/app/api/cockpit/metrics/gpu/route.ts` and `cockpit-ui/app/api/cockpit/health/route.ts`.
- Collision handling: this branch is intentionally stacked on PR #178 so those route changes are inherited instead of competing against the active PR.
- Adjacent issue: #223 remains open for telemetry route access gates. This fix is redaction only and does not treat redaction as a substitute for API-key/operator gating.

## Validation

Commands run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_telemetry_command_redaction_v1_20260602.md` - pass
- `python3 scripts/agent_job_registry.py list-active` - pass; no active jobs
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_telemetry_command_redaction_v1_20260602.md --repo-root .` - pass
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_telemetry_command_redaction_v1_20260602.md --repo-root .` - pass
- Initial direct isolated `pnpm exec vitest` - blocked by missing isolated `node_modules`; resolved by linking cached ignored dependencies from the main checkout
- `cockpit-ui/node_modules/.bin/vitest run lib/process-command-redaction.test.ts` - 6 passed
- `node_modules/.bin/eslint 'app/api/cockpit/metrics/gpu/route.ts' 'app/api/cockpit/metrics/host/route.ts' 'app/api/cockpit/health/route.ts' 'lib/process-command-redaction.ts' 'lib/process-command-redaction.test.ts'` - pass
- `node_modules/.bin/tsc --noEmit --pretty false` - pass
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_telemetry_command_redaction_v1_20260602.md` - pass
- `git diff --check` - pass

## Files Intentionally Not Touched

- Cockpit telemetry route access-gate surfaces for #223
- Cockpit UI dialogs; they continue rendering the server-redacted command strings
- Backend API routes and services
- Extraction, parser, memory, Qdrant, DB, news, and financial-truth files
- Runtime/model/GPU/service configuration

## Remaining Blockers

- #223 remains required for API-key/operator access gating of host/GPU/health telemetry routes.
- This branch depends on PR #178 because it is stacked on the active llama GPU display route changes.
