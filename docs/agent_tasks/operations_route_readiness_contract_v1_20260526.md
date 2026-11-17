---
job_id: operations_route_readiness_contract_v1_20260526
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md
  - reports/agent_jobs/operations_route_readiness_contract_v1_20260526/
  - reports/agent_jobs/operations_route_readiness_contract_v1_20260526/README.md
  - reports/agent_jobs/operations_route_readiness_contract_v1_20260526/status.json
  - reports/agent_jobs/operations_route_readiness_contract_v1_20260526/validation.json
  - reports/agent_jobs/operations_route_readiness_contract_v1_20260526/diff-check.json
  - reports/agent_jobs/operations_route_readiness_contract_v1_20260526/operations-ready.png
  - cockpit-ui/components/cockpit/operations/operations-screen.tsx
  - cockpit-ui/tests/smoke.spec.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/operations_route_readiness_contract_v1_20260526
mutation_mode: safe_extension
production_data_access: false
---

# Operations Route Readiness Contract V1

Resolve GitHub issue #110 by giving the Operations route an explicit UI readiness marker and updating smoke validation to wait for that marker rather than relying on `networkidle`.

## Scope

- Add a stable readiness marker to the rendered Operations screen once the route is hydrated.
- Update the Cockpit smoke test to verify the Operations route reaches that marker after navigation.
- Preserve all Operations action execution, job polling, backend interaction, and runtime behavior.

## Forbidden

- No backend/runtime/GPU/service config changes.
- No production DB/Qdrant/news/memory writes.
- No canonical financial truth, parser routing, extraction prompt, or gold-label changes.
- No removal of Operations smoke coverage.
- No unrelated dirty work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md`
- focused Playwright smoke for Operations readiness
- targeted ESLint for changed files
- TypeScript
- Next build if practical
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md`
