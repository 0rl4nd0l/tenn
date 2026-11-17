# Redis Runtime Role Reconciliation

Job: `redis_runtime_role_reconciliation_v1_20260531`
Issue: #143
Date: 2026-06-01
Result: complete; host Redis ownership documented for the host-network runtime

## Summary

The current host-network Tenn runtime is configured to use host Redis at
`127.0.0.1:6379`. The `fe_redis` compose container remains exited because it
also uses host networking and cannot bind the same port while the host
`redis-server` owns it.

This job did not start, stop, restart, kill, or reconfigure Redis or any Tenn
container. It preserved the current role expectation in
`docs/architecture/02_runtime_topology.md` so the bind-conflict exit is not
treated as an unexplained broker outage.

## Evidence Collected

- `docker ps -a` showed `fe_redis` as `Exited (1) 5 days ago`.
- `docker inspect fe_redis` showed `network_mode=host`, `status=exited`, and
  `exit=1`.
- `docker logs --tail 80 fe_redis` showed repeated port `6379` bind conflicts.
- `ss -ltnp 'sport = :6379'` showed listeners on localhost IPv4 and IPv6.
- `ps` identified `/usr/bin/redis-server 127.0.0.1:6379` owned by user `redis`.
- `redis-cli PING` returned `PONG` for both `127.0.0.1` and `localhost`.
- `docker inspect` for backend, worker, and GPU worker showed Redis/Celery URLs
  pointing at `redis://127.0.0.1:6379/...` with `TENN_HOST_NETWORK=true`.

## Files

- `runtime_snapshot.json`: structured runtime and source evidence.
- `redis_role_reconciliation.md`: narrative reconciliation and follow-up.
- `validation.json`: task-card validation report.
- `diff-check.json`: final allowlist check.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/redis_runtime_role_reconciliation_v1_20260531.md --write-report`: PASS
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/redis_runtime_role_reconciliation_v1_20260531.md`: PASS
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/redis_runtime_role_reconciliation_v1_20260531.md --repo-root .`: PASS
- `python3 -m json.tool reports/agent_jobs/redis_runtime_role_reconciliation_v1_20260531/runtime_snapshot.json`: PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/redis_runtime_role_reconciliation_v1_20260531.md --repo-root .`: PASS
- `python3 scripts/agent_job_registry.py release redis_runtime_role_reconciliation_v1_20260531 --repo-root .`: PASS
- `python3 scripts/agent_job_registry.py list-active --read-only`: PASS after release; no active jobs remained.
- `git diff --check`: PASS

## Remaining Blocker

No blocker remains for documenting host Redis ownership. A separate
approval-gated runtime task is still required before changing compose
dependencies, stopping host Redis, or making `fe_redis` the active broker owner.
