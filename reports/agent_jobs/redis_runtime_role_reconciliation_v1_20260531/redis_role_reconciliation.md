# Redis Role Reconciliation

Issue: #143

## Conclusion

Current runtime evidence supports host Redis as the active broker owner for the
host-network Tenn runtime. The backend, worker, and GPU worker containers are
configured with `REDIS_URL`, `CELERY_BROKER_URL`, and
`CELERY_RESULT_BACKEND` pointing at `redis://127.0.0.1:6379/...`, and host Redis
responded to `PING` on both `127.0.0.1` and `localhost`.

`fe_redis` is still an exited compose container. Its logs show Redis aborting
because port `6379` was already in use. Because `fe_redis` also uses
`network_mode: host`, that state is an ownership conflict with the host daemon,
not standalone proof that the broker configured for backend or worker traffic is
down.

## Evidence

- `docker ps -a` showed `fe_redis` as `Exited (1) 5 days ago`; backend, worker,
  and GPU worker were also stopped at collection time.
- `docker inspect fe_redis` showed `network_mode=host`, `status=exited`,
  `exit=1`, `image=redis:7`, and `restart=no`.
- `docker logs --tail 80 fe_redis` showed repeated `bind: Address already in
  use` failures for port `6379`.
- `ss -ltnp 'sport = :6379'` showed listeners on `127.0.0.1:6379` and
  `[::1]:6379`.
- `ps` identified `/usr/bin/redis-server 127.0.0.1:6379` owned by user `redis`
  with parent PID `1`.
- `redis-cli -h 127.0.0.1 -p 6379 PING` returned `PONG`.
- `docker inspect` for `fe_backend`, `fe_worker`, and `fe_gpu_worker` showed
  `REDIS_URL=redis://127.0.0.1:6379/0`,
  `CELERY_BROKER_URL=redis://127.0.0.1:6379/0`,
  `CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1`, and
  `TENN_HOST_NETWORK=true`.
- Source inspection showed `financial-engine_v2/docker-compose.yml` defines
  `fe_redis` with `network_mode: host`, while backend and worker services depend
  on the redis service with `condition: service_started`.
- Source inspection showed backend config rewrites Redis hostnames to
  `127.0.0.1` when host networking is enabled.

## Change Made

`docs/architecture/02_runtime_topology.md` now documents the host-network Redis
ownership rule:

- Host-network backend and worker containers should use
  `redis://127.0.0.1:6379/...`.
- `fe_redis` cannot run at the same time as a host `redis-server` that owns
  port `6379`.
- `fe_redis` exiting with a bind conflict should be interpreted as an ownership
  conflict, while broker health should be evaluated against the configured
  `CELERY_BROKER_URL`.
- Switching Redis ownership requires an explicit runtime change plan and queue
  safety check.

## Remaining Follow-Up

This task did not change service ownership. A separate approval-gated runtime
change is still required if Tenn wants compose `fe_redis` to become the owner or
if compose dependencies should be refactored so host Redis is the only declared
broker dependency.
