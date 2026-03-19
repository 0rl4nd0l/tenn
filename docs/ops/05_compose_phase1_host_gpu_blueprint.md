# 05 - Docker Blueprint (Phase 1: Host GPU, Ollama on Host)

Phase objective:
- Stabilize platform services in containers while keeping GPU runtime on host.
- Avoid GPU container/runtime complexity until NVML is proven stable.

This is additive to existing `financial-engine_v2/docker-compose.yml`.

## Phase-1 Design

Containers:
- Postgres
- Redis
- Qdrant
- FastAPI app
- Celery CPU workers

Host service:
- Ollama (systemd-managed on host)

Networking convention:
- Containers call host Ollama via a host-resolvable endpoint.
- Use explicit `OLLAMA_URL` in env to avoid implicit fallback behavior.
- Validate connectivity from app/worker containers before production runs.

## Files
- Compose: `docs/ops/05.compose.phase1.yml`
- Env template: `docs/ops/05.env.template`

## Volume Layout and Durability

Persistent volumes (named or bind-mounted):
- Postgres data
- Redis data (if persistence enabled)
- Qdrant storage
- App artifacts and reports
- Raw docs/PDF storage

Backups:
- Postgres: scheduled logical backups + periodic restore test
- Qdrant: snapshot/export policy + restore dry-run
- Artifacts: filesystem snapshots/rsync rotation

## Health Checks and Restart Policy Baseline

Health checks:
- Postgres readiness
- Redis ping
- Qdrant health endpoint
- FastAPI health endpoint
- Worker liveness heartbeat (queue depth + worker ping)

Restart policies:
- Service-level `unless-stopped` baseline
- Guard against crash loops with start-period and bounded retries where needed

## Upgrade Strategy

1. Pin container image tags (avoid floating latest for production).
2. Upgrade noncritical services first (Qdrant/Redis), then backend/worker.
3. Keep DB migration steps explicit and reversible.
4. Validate health and queue flow after each component upgrade.

## Data Migration Notes

If moving from legacy compose/runtime:
- Export DB data and verify schema compatibility before cutover.
- Rehydrate Qdrant collections from snapshot or deterministic re-embed jobs.
- Preserve document hashes and provenance IDs to avoid lineage breaks.

## Observability Basics

Minimum signals:
- Queue depth by queue name
- Job failure rate by task type
- Postgres connection saturation
- Qdrant upsert/search latency
- App p95/p99 API latency

Log policy:
- Structured logs with `job_run_id`, `document_id`, `ticker`, `queue`, `model_version`.

## Phase-2 Promotion Path (GPU Containers, Optional)

Promote only after:
- NVML stability acceptance suite passes (3 reboot criterion)
- Ollama GPU usage proven stable on host
- No repeated NVRM/Xid error pattern in observation window

Phase-2 additions:
- Optional GPU worker container profile
- NVIDIA container toolkit integration
- cgroup/systemd compatibility verification

Rollback gate:
- If GPU container path regresses NVML stability, revert to Phase-1 host Ollama immediately.
