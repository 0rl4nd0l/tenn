---
job_id: query_legacy_chat_route_ownership_v1_20260531
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
owner: Codex
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531
allowed_files:
  - docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/README.md
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/route_ownership_matrix.md
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/evidence_scan.json
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/status.json
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/validation.json
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/diff-check.json
inspect_only_surfaces:
  - financial-engine_v2/backend/app/main.py
  - financial-engine_v2/backend/app/routes/chat.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/tenn_chat.py
  - financial-engine_v2/backend/app/services/query_orchestrator.py
  - financial-engine_v2/shared/evidence_labels.py
  - financial-engine_v2/backend/tests/test_evidence_label_semantics.py
  - cockpit-ui/lib/api-client.ts
  - docs/architecture/19_backend_api_surface.md
  - docs/architecture/21_cockpit_client_contract.md
  - reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md
---

# Task

Audit GitHub issue #150 by classifying ownership for the live backend chat routes:

- `POST /chat`
- `POST /api/chat`
- `POST /api/cockpit/chat`

This task is report-only. It must not integrate the parked legacy envelope branch, retire any route, change source/evidence label behavior, run a live chat request, or mutate product/runtime/data surfaces.

# GitHub Tracking

- Issue: https://github.com/0rl4nd0l/tenn/issues/150
- PR link policy: use `Refs #150`; this is an audit/route-ownership classification, not validated product remediation.

# Target Layer And Contract

- Target layer: Analysis and Client route ownership.
- Relevant contract rules: backend authority; Cockpit as client/orchestration only; backend-owned retrieval; no alternate retrieval/ranking; source/evidence labels must not be weakened.
- What must not change: backend route behavior, retrieval ranking, ingestion, Qdrant, Postgres, news stores, memory stores, financial truth/extraction, source/evidence label semantics, Cockpit UI behavior, runtime/model/GPU/service config, and unrelated dirty work.
- Safety basis: writes are limited to task/report artifacts. Runtime/backend/frontend files are inspected only.
- GPU process check required: no.

# Required Analysis

1. Prove how `chat_router` is mounted.
2. Classify current ownership for `/chat`, `/api/chat`, and `/api/cockpit/chat`.
3. Determine whether the current legacy route has source labels, a route-level source-label taxonomy version, and a compatibility envelope.
4. Determine whether the Cockpit web UI calls the legacy route or the Cockpit route.
5. Check current branch coverage against parked legacy-envelope work and duplicate GitHub trackers.
6. Record whether issue #150 can close or should remain open for implementation/deprecation follow-up.

# Hard Stops

Stop and report only if:

- a duplicate PR already fully covers #150
- implementation would require editing contested chat/runtime surfaces
- source/evidence label honesty would need to be weakened
- production data access would be required
- live `/api/cockpit/chat` smoke would persist chat/diagnostic state

# Validation

Run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- route/evidence `rg` scans recorded in `evidence_scan.json`
- JSON parse checks
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- `git diff --check`
- `git diff --cached --check`
- `python3 scripts/agent_job_registry.py release query_legacy_chat_route_ownership_v1_20260531`

# Definition Of Done

- Route ownership is recorded with current repo evidence.
- The legacy route's current evidence-label/taxonomy/envelope state is recorded.
- Parked legacy-envelope branch evidence is linked.
- Required follow-up status is explicit.
- No forbidden surface is changed.
