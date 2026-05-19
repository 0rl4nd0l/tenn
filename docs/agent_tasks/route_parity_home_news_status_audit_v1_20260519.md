---
job_id: route_parity_home_news_status_audit_v1_20260519
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519
mutation_mode: audit_only
production_data_access: false
allow_audit_code_changes: true
---

# Task

Audit current route parity expectations after the validated NVMe2 migration.

Determine whether backend `/api/cockpit/home` and `/api/news/status` should exist, or whether the current frontend BFF-only behavior is intentional and correct.

# Hard boundaries

Do not implement routes.
Do not edit backend/frontend source files.
Do not change runtime bindings, `/data`, `/reports`, DBs, Qdrant, news stores, memory, Docker volumes, systemd services, model config, or CUDA/M40 runtime.
Do not use production data beyond read-only route/file inspection and limited smoke checks needed to classify route behavior.

# Context

The NVMe2 storage/runtime migration is considered validated. Final route smoke reportedly found:
- backend `/api/cockpit/home` missing as a direct backend route;
- frontend `/api/cockpit/home` BFF exists and returns HTTP 200;
- `/api/news/status` missing in this branch/profile;
- Home returns `data_state: PARTIAL` and honest `DATA_MISSING` markers;
- this is not a storage migration blocker.

The current question is route contract/product completeness, not storage migration.

# Required preflight

Run and report:
- `pwd`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- recent commits relevant to Cockpit Home/news/routes
- active task card discovery, if supported
- registry/list-active, if supported
- dirty/untracked/deleted files touching backend routes, cockpit-ui routes, news, Home, BFF, docs, or tests

# Inspect

Focus on:
- backend route registration for Cockpit/Home/news/status
- Next.js BFF routes for Cockpit Home
- frontend call sites expecting `/api/cockpit/home`
- frontend/backend call sites expecting `/api/news/status`
- route tests, smoke tests, docs, task cards, reports mentioning these routes
- final NVMe2 route-contract report if present:
  `reports/agent_jobs/nvme2_route_contract_frontend_smoke_final_v1_20260518/`

# Required classification

For each route:

## `/api/cockpit/home`
Classify one:
- backend route required and missing
- frontend BFF route intentionally owns this path
- compatibility/deprecated route
- docs/test drift
- DATA_MISSING

## `/api/news/status`
Classify one:
- backend route required and missing
- frontend route required and missing
- deprecated/old docs only
- intentionally absent in this branch/profile
- docs/test drift
- DATA_MISSING

# Required output

Write report to:

`reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/README.md`

Include:
- Confirmed facts
- Inferred facts
- Speculative claims
- DATA_MISSING
- files/docs/tests/reports inspected
- current route ownership map
- whether each route gap is a blocker, product completeness issue, stale expectation, or no issue
- collision risks
- recommended next safe step
- whether implementation appears LOW / MEDIUM / HIGH risk
- exact validation/smoke commands run and results
- final git status
- Project Memory save recommendation

# Hard stops

Stop and report only if:
- active registry shows overlapping Reporting/Query Orchestration route work
- dirty files touch route surfaces and cannot be safely classified
- smoke would require mutating data/runtime bindings
- route behavior depends on unavailable services
- any implementation appears necessary before classification
