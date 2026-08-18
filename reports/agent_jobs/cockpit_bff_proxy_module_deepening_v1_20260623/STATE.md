# Cockpit BFF Proxy Module Deepening State

## Git State

- Worktree: `/home/l4nd0/tenn-cockpit-bff-proxy-deepening-v1-20260623-pr`
- Branch: `dev-flow/cockpit-bff-proxy-deepening-v1-20260623-pr`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base HEAD at branch creation: `6df3b29783dffe625f74dfbb4870667a4c57b750`
- Task card: `docs/agent_tasks/cockpit_bff_proxy_module_deepening_v1_20260623.md`

## Guard State

- `tenn-git-guard` preflight: pass.
- Registry `list-active --read-only`: no active jobs.
- Task ledger validation: pass; live and committed ledgers available.
- Duplicate PR search for Cockpit proxy work: no blocking active PR found.

## Owner-Boundary Dirt

The source worktree used during the first implementation pass had unrelated
dirty Tenn guard files. The final PR branch was rebuilt in this clean sibling
worktree so the task-card diff gate can evaluate only this lane.

## Implementation State

- Added `proxyBackendRequest`, `buildBackendResponse`, and `resolveBackendPath`
  to `cockpit-ui/lib/proxy.ts`.
- Kept `proxy.ts` portable by using the standard Web `Response` rather than
  importing `next/server`.
- Migrated only the watchlist BFF route cluster to the shared proxy helper.
- Added focused proxy helper tests.

## Docs Impact

- `docs_impact`: `DOCS_NOT_REQUIRED`
- `docs_checked`:
  - `reports/agent_jobs/repo_architecture_development_board_v1_20260623/BOARD.md`
  - `reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623/NEXT_GOAL.md`
  - `cockpit-ui/lib/proxy.ts`
- `docs_changed`: `NONE`
- `docs_followup`: `NONE`
- `reason`: Internal Cockpit BFF helper refactor with no API, operator workflow,
  runtime, or data contract change.

## Model And Worker Routing

- `task_tier`: `medium`
- `recommended_model`: `standard coding model`
- `actual_model`: `Codex GPT-5`
- `why_this_model`: Focused TypeScript route-helper refactor with existing route
  tests.
- `worker_model_allowed`: `false`
- `worker_decision_limit`: Main orchestrator only; no subagent needed for this
  narrow slice.
- `escalation_needed`: `false`
