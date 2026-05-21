---
job_id: route_parity_home_news_status_audit_v1_20260521
lane: Reporting
owner: Codex
mutation_mode: audit_only
production_data_access: false
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521
allowed_files:
  - docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md
  - reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/
---

# Task

Audit Tenn route parity after the validated NVMe2 migration.

Primary lane: Reporting. Supporting lanes: Query Orchestration, Evaluation, Repo Hygiene.

Determine whether `/api/cockpit/home` and `/api/news/status` should exist as backend routes, frontend BFF routes, deprecated/compatibility routes, or whether current expectations are docs/test drift.

# Mode

AUDIT ONLY. Do not implement routes.

# Context

NVMe2 migration is considered validated. M40 runtime is restored. Current baseline branch is reportedly `migration/clean-runtime-baseline-reconstruct-v1`.

A prior route smoke reportedly found:

- backend `/api/cockpit/home` does not exist as a direct backend aggregate route;
- frontend `/api/cockpit/home` BFF exists and returned HTTP 200;
- `/api/news/status` does not exist in this branch/profile;
- Home returned `data_state: PARTIAL` with honest `DATA_MISSING` markers;
- this was not considered a storage migration blocker.

Recent baseline: ASX document-type sidecar artifacts landed on `migration/clean-runtime-baseline-reconstruct-v1` at commit `8e38d26725e3` with clean status and no parser routing/canonical write changes. Treat this as background only; do not touch Financial Truth/extraction surfaces.

# Allowed Work

- Inspect code, docs, tests, task cards, reports, and route registration read-only.
- Write only this task card and report artifacts under `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/`.
- Run task-card validation, registry checks, overlap checks, `git diff --check`, and task-card `check-diff`.
- Run limited non-mutating route smokes only if existing services can be safely queried without changing runtime binding or data.

# Required Preflight

Run and report:

- `pwd`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git log --oneline -20`
- active task card discovery if supported
- registry/list-active if supported
- check-overlap for this task card if supported
- dirty/untracked/deleted file classification for backend routes, cockpit-ui routes, news, Home, BFF, docs, or tests

# Inspect

- backend route registration and route files for Cockpit/Home/news/status
- Next.js BFF route files for Cockpit Home and news/status
- frontend call sites expecting `/api/cockpit/home`
- frontend/backend call sites expecting `/api/news/status`
- route tests, smoke tests, docs, task cards, and reports mentioning either route
- prior report if present: `reports/agent_jobs/nvme2_route_contract_frontend_smoke_final_v1_20260518/`
- current Cockpit Home / route parity reports if present

# Required Classification

Classify `/api/cockpit/home` as one:

- backend route required and missing
- frontend BFF route intentionally owns this path
- compatibility/deprecated route
- docs/test drift
- DATA_MISSING

Classify `/api/news/status` as one:

- backend route required and missing
- frontend route required and missing
- deprecated/old docs only
- intentionally absent in this branch/profile
- docs/test drift
- DATA_MISSING

# Forbidden

Do not implement routes.
Do not edit backend/frontend source files.
Do not change `/data` or `/reports` bindings.
Do not touch DBs, Qdrant, news stores, memory, Docker volumes, systemd services, model config, CUDA/M40 runtime, parser/extraction surfaces, canonical truth, generated sidecars, or production data.
Do not start Home producer implementation.
Do not remove `PARTIAL` or `DATA_MISSING` honesty.

# Hard Stops

- HIGH registry/lane/file collision
- dirty route files cannot be safely classified
- task card invalid or impossible to validate
- smoke requires mutating runtime/data
- any required action touches forbidden surfaces
- production data mutation would be needed

# Required Report

Write `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/README.md` including:

- branch, HEAD, git status, worktrees
- task card status
- registry/active jobs status if available
- files/docs/tests/reports inspected
- Confirmed / Inferred / Speculative / DATA_MISSING
- route ownership map
- verdict for each route
- whether each gap is blocker, product-completeness issue, stale expectation, or no issue
- exact commands/smokes run and results
- implementation risk rating LOW/MEDIUM/HIGH
- recommended next safe step
- final git status
- Project Memory save recommendation
