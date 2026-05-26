---
job_id: a2m_backend_reload_news_status_activation_smoke_v1_20260525
lane: Query Orchestration
supporting_lanes:
  - Runtime/Performance
  - Provenance
  - Reporting
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/**
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/README.md
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/status.json
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/runtime_reload_trace.json
  - reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/diff-check.json
approval_required: true
runtime_approval_scope: reload/restart fe_backend only
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525
mutation_mode: audit_only
production_data_access: false
allowed_runtime_action:
  - reload/restart fe_backend only, using the least disruptive project-standard method discovered from repo/docker compose context
---

# A2M Backend Reload News Status Activation Smoke

Audit-only runtime smoke for A2M news-status activation after commit
`c8d605e3de625c9f456edc0f3896b571a68f6b25` landed.

Primary lane: Query Orchestration.

Supporting lanes:

- Runtime/Performance
- Provenance
- Reporting
- Evaluation
- Repo Hygiene

## Objective

Verify whether reloading or restarting only `fe_backend` activates
`GET /api/cockpit/news/status`, then rerun the smallest A2M route and chat
smoke needed to classify the current runtime behavior. Do not implement fixes.

## Allowed Writes

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/**`

## Approved Runtime Action

- Reload or restart `fe_backend` only, using the least disruptive
  project-standard method discovered from repo and Docker Compose context.

## Forbidden

- Code changes.
- DB, Qdrant, news-store, Tenn memory, or canonical financial truth mutation.
- Reindex, resync, backfill, projection repair, projection rebuild, parser
  routing, source-label/ranking/synthesis/prompt/UI fixes, or runtime/model/GPU
  config edits.
- Restarting `llama-server`, Qdrant, Postgres, Next server, or unrelated
  services unless the project-standard backend restart command necessarily
  touches only backend dependencies and this is reported.
- Changing `.env`, Compose files, runtime/model config, volumes, DB, Qdrant, or
  news stores.
- Cleaning, stashing, resetting, deleting, moving, committing, or otherwise
  touching unrelated files or foreign task cards.

## Required Preflight

1. Record branch, HEAD, worktree, and `git status --short --untracked-files=all`.
2. Record `git worktree list`.
3. Validate this task card.
4. Run registry/list-active.
5. Run registry/check-overlap and stop on active Query Orchestration overlap.
6. Identify current `fe_backend` container/process start time.
7. Capture current `/api/cockpit/news/status` before reload.
8. Capture current `/openapi.json` relevant cockpit paths before reload.
9. Record known foreign untracked task cards and do not touch them.

## Runtime Action

- Determine the least disruptive standard restart or reload method for
  `fe_backend` from repo/Docker Compose context.
- Restart or reload `fe_backend` only.
- Do not rebuild images unless required and explicitly justified.
- Record the exact command used.

## Post-Reload Checks

- Confirm `fe_backend` is running.
- Capture new process/container start time.
- `GET /api/cockpit/health`.
- `GET /api/cockpit/config`.
- `GET /openapi.json` and confirm whether `/api/cockpit/news/status` appears.
- `GET /api/cockpit/news/status` and record HTTP status/body summary.
- Run one 30s stateless A2M chat probe with `web_search=false`, `rag=true`,
  `stream=false`, and `stateless_smoke=true`.
- If safe, run the prior "use only local_news_context" A2M probe once more.
- Record source labels, `source_coverage_status`,
  `claim_verified_source_count`, `local_news_context` count, and whether final
  answer text aligns with the returned `local_news_context` source.

## Hard Stops

Stop if registry shows active Query Orchestration overlap, if backend reload
requires forbidden mutation, or if no narrow backend-only restart method is
available.

## Required Outputs

- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/README.md`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/status.json`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/runtime_reload_trace.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md --repo-root .`
- JSON validation for generated artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- Final `git status --short --untracked-files=all`.
