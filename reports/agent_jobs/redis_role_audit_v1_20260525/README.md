# Redis Role Audit

## Scope

- GitHub issue: #59.
- Lane: Reporting.
- Execution mode: AUDIT MODE.
- Target system layer: runtime/ops documentation and dependency classification only.
- Contract boundary: no service starts/stops, Docker/env/config/source/runtime/data-store changes, or Redis mutation.

## Findings

1. Redis is a first-class full-stack dependency in Compose. `financial-engine_v2/docker-compose.yml` defines `redis:7` as `fe_redis`, and backend, worker, GPU worker, and beat services depend on Redis service start.
2. Redis is the Celery broker and result backend. `financial-engine_v2/backend/app/celery_app.py` writes normalized `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` into env, then configures Celery `broker_url`, `result_backend`, and specialized queues.
3. Worker docs classify Redis as broker/backend and state that the adaptive router uses Redis queue-depth probes when reachable. Evidence: `docs/architecture/09_worker_and_celery_contract.md:48-69`.
4. Redis also carries transient runtime coordination state. `router_state.py` uses Redis for queue depths and extraction/GPU-exclusive activity tokens, but falls back to a shared file when Redis is unavailable.
5. Backend and Cockpit health surfaces probe Redis connectivity and queue depths. Evidence: `financial-engine_v2/backend/app/main.py:1276-1305`, `main.py:2112-2148`, and `cockpit_api.py:3874-3970`.
6. Redis is not authoritative financial truth. No evidence showed Redis storing canonical metrics, source labels, memory truth, Qdrant vectors, or Postgres-owned facts.

## Classification

- Required for: Celery mode, Compose full-stack workers, queue status, and Redis-backed router/extraction coordination.
- Optional/degraded for: sync or isolated backend paths where broker-backed ingestion is not required. `scripts/check_environment.py` makes Redis required only when `task_mode` is not `sync`; `main.py` logs continued operation without broker-backed ingestion when not in Celery mode.
- Disabled/stale: not confirmed.
- Queue-only: false. Redis is queue/broker/result backend plus transient runtime coordination.
- Cache-like: partial. It stores transient runtime state and queue metadata, not canonical business data.

## Risks And Gaps

- Confirmed: docs use both broker and cache language; operators may not know which features degrade when Redis is down.
- Confirmed: queue-depth and health endpoints depend on Redis reachability for accurate queue status.
- Inferred: if Redis is down while `TASK_MODE=celery`, queued ingestion and worker execution are effectively unavailable.
- DATA_MISSING: live Redis process status was not sampled because this audit forbids service operations and does not require live runtime probing.

## Recommended Child Task

`redis_role_docs_and_health_semantics_v1_20260525`

Clarify in docs and health/status labels that Redis is:

- required for Celery worker execution and queue/result state,
- optional for sync/isolated backend mode,
- used for transient router/extraction coordination with file fallback,
- never a source of canonical financial truth.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/redis_role_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/redis_role_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/redis_role_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release redis_role_audit_v1_20260525`: passed.
- `python3 -m json.tool reports/agent_jobs/redis_role_audit_v1_20260525/redis_usage_inventory.json`: passed.
- `python3 -m json.tool reports/agent_jobs/redis_role_audit_v1_20260525/status.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/redis_role_audit_v1_20260525.md`: passed.
