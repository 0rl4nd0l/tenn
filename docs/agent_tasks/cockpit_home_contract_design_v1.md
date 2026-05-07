---
job_id: cockpit_home_contract_design_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_contract_design_v1.md
  - reports/agent_jobs/cockpit_home_contract_design_v1/**
  - cockpit-ui/types/cockpit-home.ts
  - cockpit-ui/lib/cockpit-home-contract.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_home_contract_design_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Create a narrow Cockpit Home backend/BFF contract design and frontend TypeScript contract scaffold.

Primary lane: Reporting
Supporting lanes: Query Orchestration, Provenance

# Context

Cockpit Home V0 landed at `4f9736ce7d68`.

Audit report:
`reports/agent_jobs/cockpit_home_backend_bff_contract_audit_v1/README.md`

Audit findings:
- Home is currently mock-backed and client-side only.
- Existing useful surfaces include holdings, health/queue/verification, `/rag/query source=news`, `/api/context/ticker`, commentary recent sources, and `/api/cockpit/chat` attached sources.
- Missing contracts include Home state, ASX market session/calendar, Home news summary, source detail resolver, data-health summary, source-label mapping, and selected-source chat handoff.
- Home chat handoff should preserve `ChatScreen` and use `/api/cockpit/chat` with backend-resolvable attached sources.
- Do not wire live data yet.

# Goal

Add a frontend contract/spec scaffold only. Do not implement runtime fetching or backend endpoints yet.

The output should define:
1. A typed `CockpitHomeBffResponse` or equivalent.
2. Deterministic Home state fields.
3. Source/evidence identity fields for source-bearing Home items.
4. Backend snake_case source-label to Home display-label mapping.
5. DATA_MISSING / degraded semantics.
6. Attached-source handoff shape for preserved ChatScreen.
7. Acceptance tests for trust-label mapping and contract invariants.

# Allowed work

Allowed:
- Add or update a small frontend contract/type file.
- Add focused frontend unit tests for contract mapping/invariants.
- Write final report under `reports/agent_jobs/cockpit_home_contract_design_v1/`.

Preferred files:
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`

# Forbidden work

Do not:
- create `GET /api/cockpit/home` yet
- wire Home to live data
- edit backend runtime code
- edit `financial-engine_v2/backend/app/routes/cockpit_api.py`
- edit `financial-engine_v2/backend/app/services/cockpit_service.py`
- edit `financial-engine_v2/backend/app/services/query_orchestrator.py`
- edit `financial-engine_v2/cockpit/core/chat.py`
- mutate databases, Qdrant, news stores, memory stores, or production/local data
- run ingestion/reindex/resync jobs
- change legacy `/chat`
- add hidden fallback retrieval paths
- let LLM output define canonical numbers, source IDs, evidence IDs, health states, or trust labels

# Required preflight

Run and report:
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_contract_design_v1.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_contract_design_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn`

Claim the registry job only if safe.

# Hard stops

Stop and report only if:
- registry overlap is found
- dirty files overlap the allowed surfaces
- task-card validation fails
- backend runtime edits appear necessary
- production data access would be required
- collision risk becomes HIGH

# Validation

Run focused validation only:
- relevant frontend unit test for the new contract/mapping file
- TypeScript check if scoped and practical
- `git diff --check`
- task-card `check-diff`

# Final report

Write:

`reports/agent_jobs/cockpit_home_contract_design_v1/README.md`

Include:
1. Branch / HEAD / worktree / dirty status
2. Task card and registry status
3. Files changed
4. Contract fields added/designed
5. Source-label mapping rules
6. DATA_MISSING / degraded semantics
7. Attached-source handoff shape
8. Tests run and exact results
9. Collision risk
10. DATA_MISSING
11. Recommended next safe implementation step
12. Project Memory save recommendation
