---
job_id: cockpit_boot_health_bff_contract_v1_20260531
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md
  - reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531/README.md
  - reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531/status.json
  - reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531/validation.json
  - reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531/diff-check.json
  - cockpit-ui/components/cockpit/boot/boot-screen.tsx
  - cockpit-ui/lib/boot-health.test.tsx
  - cockpit-ui/tests/chat-browser-regression.spec.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Boot Health BFF Contract

Safe-extension task for issue #144.

## Lane

Primary lane: Reporting.

Supporting lanes: Runtime, Evaluation.

## Objective

Route the `/boot` readiness screen through the Cockpit health BFF at
`/api/cockpit/health` instead of direct browser-local runtime probes.

## Scope

Allowed:

- Create this task card and report artifacts.
- Update `cockpit-ui/components/cockpit/boot/boot-screen.tsx` so Boot consumes
  the BFF health envelope as the authoritative readiness source.
- Add focused Boot health tests.
- Extend existing browser route coverage so `/boot` is included.

Forbidden:

- Do not mutate DB, Qdrant, news, memory, or other data stores.
- Do not change canonical financial truth, parser routing, extraction prompts,
  gold labels, model/runtime/GPU/service config, Docker, cron, or service
  lifecycle.
- Do not start, stop, or restart runtime services.
- Do not perform broad UI redesign or global chrome refactors.
- Do not touch unrelated dirty work.

## Acceptance Criteria

- `/boot` fetches `/api/cockpit/health` as the readiness source.
- Browser-only localhost probes for llama.cpp, Ollama, Qdrant, and Redis are
  removed from readiness status.
- Redis, Qdrant, llama.cpp, Ollama, GPU, and host states render from the BFF
  envelope where available.
- Unknown status remains visible only when the BFF cannot verify a service.
- Route/browser coverage includes `/boot`.
- No runtime services or data stores are mutated.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md`
- focused Boot health unit test
- route smoke or browser route coverage including `/boot`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md`
- release the registry claim before final report
