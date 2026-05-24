# Runtime Topology Reconciliation Audit

Job: `runtime_topology_reconciliation_audit_v1_20260522`
Date: 2026-05-24
Mode: audit only, approval gated

## Confirmed Facts

- Canonical entrypoint: `/home/l4nd0/tenn`.
- Canonical resolved path: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `/home/l4nd0/tenn-runtime` also resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Canonical HEAD: `e170f6b255ca4229462d4167861775e82ea3df34`.
- Canonical git common dir: `/mnt/sdb2/home/l4nd0/tenn/.git`.
- Agent registry root: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`.
- Active registry overlap check was clean before claim. The only active job after claim was this audit.
- Docker `fe_backend`, `fe_worker`, and `fe_gpu_worker` are running from bind mounts under `/home/l4nd0/tenn-fast-dev-storage-v1`.
- Docker `fe_backend`, `fe_worker`, and `fe_gpu_worker` compose labels point to working dir `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2` and config file `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/docker-compose.yml`.
- Docker `fe_qdrant`, `fe_postgres`, and exited `fe_redis` compose labels point to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/docker-compose.yml`.
- `fe_qdrant` and `fe_postgres` use Docker volume storage under `/mnt/nvme/docker/volumes/...`, not repo-local bind mounts.
- `tenn-cockpit-ui-frontend.service` is active as a transient user unit with `WorkingDirectory=/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui`.
- Installed user llama units point to `/home/l4nd0/tenn-runtime`, but repo template `systemd/llama-cpp-router.service` still points to `/mnt/sdb2/home/l4nd0/tenn`.
- User crontab runs nightly news from `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`.
- `/data` resolves to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`.
- `/reports` resolves to `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports`.
- `/mnt/tenn-nvme2` is backed by `/dev/nvme0n1p1` as ext4 with `rw,noatime`.
- `/home/l4nd0/tenn`, `/home/l4nd0/tenn-runtime`, `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`, and `/home/l4nd0/tenn-fast-dev-storage-v1` are on `/dev/nvme1n1p1`.
- `/mnt/sdb2` is backed by `/dev/sdc2` as ext4.
- `scripts/verify_nvme_runtime_endpoints.sh` passed and reported `NVME_RUNTIME_ENDPOINTS_OK=1`.

## Inferred Facts

- The runtime is split: active backend and workers are still fast-dev code, while qdrant/postgres/redis compose metadata already reflects canonical compose.
- Recreating backend/worker/gpu_worker from canonical compose would change both code source and `/data` binding. Current fast-dev compose mounts `./data:/data`; canonical compose mounts `/mnt/tenn-nvme2/tenn/financial-engine_v2/data:/data`.
- Cron cannot be safely repointed to canonical yet: canonical `/home/l4nd0/tenn/integrations/newspaper4k_au/.venv/bin/activate` is missing, while the `/mnt/sdb2` checkout has that venv.
- Rebinding Cockpit UI to canonical may break LAN/Tailscale dev access unless the fast-dev local Next.js config change is preserved or intentionally replaced.
- `/home/l4nd0/tenn-fast-dev-storage-v1` has no unique commits relative to canonical, but it has tracked local modifications and many untracked production/evaluation-relevant files that must be checkpointed before retirement.
- The git common-dir and registry root being under `/mnt/sdb2/home/l4nd0/tenn/.git` is a worktree artifact, not proof that `/mnt/sdb2/home/l4nd0/tenn` is the active runtime checkout. It is still operationally confusing and should be documented.

## DATA_MISSING

- No restart/recreate validation was run, by policy.
- No live service logs were tailed.
- No runtime data stores were queried or modified.
- No Docker volume contents were inspected.
- No cron dry-run was executed.
- No proof that fast-dev untracked Appendix 5B and evaluation files are obsolete. Treat them as production-relevant until reviewed.
- No proof that canonical `integrations/newspaper4k_au` can run nightly news without building its missing venv.
- No proof that the transient Cockpit UI unit can be replaced by the repo launcher without changing user-visible behavior.

## Canonical Path

| Item | Value |
| --- | --- |
| User-facing canonical repo path | `/home/l4nd0/tenn` |
| Resolved repo path | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Runtime symlink | `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Previous symlink target marker | `/home/l4nd0/tenn.previous_symlink_target_20260521 -> /mnt/hdd-data/home/l4nd0/tenn` |
| Canonical branch | `migration/clean-runtime-baseline-reconstruct-v1` |
| Canonical HEAD | `e170f6b255ca4229462d4167861775e82ea3df34` |
| Git common dir | `/mnt/sdb2/home/l4nd0/tenn/.git` |
| Registry root | `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry` |

## Live Runtime Binding Table

| Surface | Current path | Desired path | Risk | Required change | Validation |
| --- | --- | --- | --- | --- | --- |
| Docker backend code | `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/backend -> /app` | `/home/l4nd0/tenn/financial-engine_v2/backend` via canonical compose | HIGH | Checkpoint fast-dev changes, then recreate backend from canonical compose | `docker inspect fe_backend` mounts and labels; `/api/health`; git provenance env shows canonical HEAD |
| Docker worker code | `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/backend -> /app` | `/home/l4nd0/tenn/financial-engine_v2/backend` | HIGH | Recreate worker from canonical compose after preserving fast-dev changes | `docker inspect fe_worker`; queue health; Celery logs |
| Docker GPU worker code | `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/backend -> /app` | `/home/l4nd0/tenn/financial-engine_v2/backend` | HIGH | Recreate gpu_worker from canonical compose after preserving fast-dev changes | `docker inspect fe_gpu_worker`; GPU worker queue smoke |
| Docker `/data` for backend/workers | fast-dev repo local `financial-engine_v2/data` | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data` | HIGH | Recreate with canonical compose only after confirming data source expectations | Container mount check; `scripts/verify_nvme_runtime_endpoints.sh`; app health |
| Docker reports mounts | fast-dev repo `reports` and `/workspace/reports` | `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports` | MEDIUM | Recreate with canonical compose | Container mount check; report write smoke only if approved |
| Docker qdrant | Compose label canonical, named volume `/mnt/nvme/docker/volumes/financial-engine_v2_fe_qdrant/_data` | Keep volume and service unchanged unless stack maintenance is approved | MEDIUM | No repo-path rebind needed | `docker inspect fe_qdrant`; Qdrant health |
| Docker postgres | Compose label canonical, named volume `/mnt/nvme/docker/volumes/financial-engine_v2_fe_pgdata/_data` | Keep volume and service unchanged unless stack maintenance is approved | MEDIUM | No repo-path rebind needed | `docker inspect fe_postgres`; healthcheck |
| Docker redis | Exited container with canonical compose labels | Canonical compose, running if required | MEDIUM | Decide if Redis should be started during approved stack reconciliation | `docker ps -a`; compose ps; app queue checks |
| Cockpit UI service | `/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui` | `/home/l4nd0/tenn/cockpit-ui` | HIGH | Preserve fast-dev UI changes, then replace transient user unit or launch via canonical `scripts/cockpit` | `systemctl --user show`; browser smoke; API URL check |
| Cron nightly news | `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh` | `/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh` after venv exists | HIGH | Build or approve canonical newspaper4k venv, then edit crontab | `crontab -l`; dry-run under canonical; log path check |
| Installed llama user units | `/home/l4nd0/tenn-runtime` | Acceptable, because it resolves to canonical; document as alias | LOW/MEDIUM | No runtime change required; update stale repo template later | `systemctl --user show`; `readlink -f /home/l4nd0/tenn-runtime` |
| Repo llama service template | `/mnt/sdb2/home/l4nd0/tenn` | `/home/l4nd0/tenn` or `/home/l4nd0/tenn-runtime` | MEDIUM | Docs/template-only follow-up after approval | `rg`; unit diff review |
| Codex automation timers | `TENN_CODEX_AUTOMATION_TARGET_WORKTREE=/home/l4nd0/tenn-fast-dev-storage-v1` | `/home/l4nd0/tenn` if these timers remain active | HIGH | Audit automation ownership, then edit user units/config only with approval | `systemctl --user show`; timer dry-run if approved |
| `/data` host alias | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data` | Keep | LOW | No change | `readlink -f /data`; verifier |
| `/reports` host alias | `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports` | Keep | LOW | No change | `readlink -f /reports`; verifier |

## Docker Findings

Running containers from `docker ps`:

- `fe_backend financial-engine_v2-backend Up 2 days`
- `fe_worker financial-engine_v2-worker Up 2 days`
- `fe_gpu_worker financial-engine_v2-gpu_worker Up 2 days`
- `fe_qdrant qdrant/qdrant:latest Up 2 days`
- `fe_postgres postgres:16 Up 2 days (healthy)`

Additional container state:

- `fe_redis redis:7 Exited (1) 2 days ago`

Backend and worker bind mounts:

- `fe_backend`: fast-dev backend at `/app`, fast-dev repo at `/workspace`, fast-dev scripts/config/shared/cockpit, fast-dev `financial-engine_v2/data` at `/data`, and fast-dev `reports` paths.
- `fe_worker`: fast-dev backend/shared/data.
- `fe_gpu_worker`: fast-dev backend/shared/data.

Canonical compose differs materially:

- `financial-engine_v2/docker-compose.yml` in canonical binds `/mnt/tenn-nvme2/tenn/financial-engine_v2/data:/data`.
- It binds `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports` for reports/workspace reports.
- It binds `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1:/workspace:ro`.
- It uses relative `./backend` and `./shared`, so running compose from canonical `ENGINE_ROOT` would bind canonical code.

Docker named volume finding:

- `fe_qdrant` storage is a Docker volume under `/mnt/nvme/docker/volumes/financial-engine_v2_fe_qdrant/_data`.
- `fe_postgres` storage is a Docker volume under `/mnt/nvme/docker/volumes/financial-engine_v2_fe_pgdata/_data`.
- Those storage paths are independent of the backend source checkout.

## Systemd Findings

Active Tenn-related user units:

- `tenn-cockpit-ui-frontend.service` is active and transient.
- `mnt-tenn\x2dnvme2.mount` is active.
- Tenn Codex timers are enabled; associated services are inactive/dead when inspected.

Key service paths:

- `tenn-cockpit-ui-frontend.service`
  - `WorkingDirectory=/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui`
  - `ExecStart=/usr/bin/env ./node_modules/.bin/next dev -H 0.0.0.0 -p 3000`
  - `Environment=NEXT_PUBLIC_API_URL=http://localhost:8000`
  - `FragmentPath=/run/user/1000/systemd/transient/tenn-cockpit-ui-frontend.service`
- `llama-cpp-router.service` and `llama-cpp-qwen25.service`
  - installed user units point to `/home/l4nd0/tenn-runtime`
  - inactive/dead at audit time
- `tenn-codex-*` services
  - `WorkingDirectory=/home/l4nd0/tenn-codex-automations-v1-20260516`
  - `TENN_CODEX_AUTOMATION_TARGET_WORKTREE=/home/l4nd0/tenn-fast-dev-storage-v1`
  - timers enabled

## Cron Findings

User crontab:

```cron
0 2 * * * /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
```

The nightly script derives `TENN_ROOT` from its own path. Therefore current cron execution uses `/mnt/sdb2/home/l4nd0/tenn` as the root, not canonical.

Prerequisite check:

- `/mnt/sdb2/home/l4nd0/tenn/integrations/newspaper4k_au/.venv/bin/activate` exists.
- `/home/l4nd0/tenn/integrations/newspaper4k_au/.venv/bin/activate` is missing.
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python` exists.

Conclusion: do not repoint cron until the canonical newspaper4k venv exists or the task approves rebuilding it.

## `/data` And `/reports` Findings

- Host `/data` is a symlink to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`.
- Host `/reports` is a symlink to `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports`.
- `scripts/verify_nvme_runtime_endpoints.sh` confirmed expected NVMe data, reports, models, llama binary, and config references.
- Active backend/worker containers do not currently use host `/data`; they bind fast-dev `financial-engine_v2/data` to container `/data`.
- Rebinding containers from canonical compose changes container `/data` to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`.

## Git Common Dir And Registry Root

The canonical worktree is a linked worktree whose git common dir is:

```text
/mnt/sdb2/home/l4nd0/tenn/.git
```

The agent registry root is:

```text
/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry
```

This is expected for the current worktree layout but high-confusion. It means registry metadata lives under the old `/mnt/sdb2` checkout's `.git`, even when the active working tree is `/home/l4nd0/tenn`. Future instructions should distinguish git metadata storage from runtime/source roots.

## Fast-Dev Dirty-State Assessment

Fast-dev path:

```text
/home/l4nd0/tenn-fast-dev-storage-v1
```

Fast-dev branch and relationship:

- Branch: `migration/clean-runtime-baseline-20260517`.
- HEAD: `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`.
- `migration/clean-runtime-baseline-20260517` is an ancestor of canonical `migration/clean-runtime-baseline-reconstruct-v1`.
- Rev-list count fast-dev vs canonical: `0 33`. Fast-dev has no unique commits; canonical has 33 commits ahead.

Tracked modifications in fast-dev:

- `cockpit-ui/next-env.d.ts`
- `cockpit-ui/next.config.mjs`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- `docs/validation_baseline.md`

Tracked diff summary:

- `cockpit-ui/next-env.d.ts` references `.next/dev/types/routes.d.ts`.
- `cockpit-ui/next.config.mjs` adds `allowedDevOrigins: ['100.122.176.103', 'localhost', '127.0.0.1']`.
- Docs add Appendix 5B validation/no-regression gate notes.

Untracked production/evaluation-relevant examples in fast-dev:

- `financial-engine_v2/backend/app/services/asx_appendix5b_candidate_artifacts.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_candidate_scorer.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_confirmed_label_importer.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_label_review_packet.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_manifest_builder.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_parser.py`
- Multiple matching backend tests.
- Multiple matching `financial-engine_v2/scripts/*appendix5b*` and extraction evaluation scripts.

Representative checked files above are missing from canonical. Therefore fast-dev must not be retired or rebased away until these files are reviewed and preserved or explicitly discarded by the user.

## Old Or Stale Path References

Current config/docs/scripts with path references found by `rg` excluding reports, task cards, venvs, node_modules, and runtime data:

- `systemd/llama-cpp-router.service`
  - `/mnt/sdb2/home/l4nd0/tenn`
  - stale relative to installed user units and canonical path.
- `financial-engine_v2/scripts/nightly_news.sh`
  - crontab comment still shows `/mnt/sdb2/home/l4nd0/tenn/...`.
  - the actual installed crontab also uses that path.
- `scripts/storage_guard.py`
  - default `TENN_CANONICAL_ROOT` is `/mnt/sdb2/home/l4nd0/tenn`.
  - final confirmation text references `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2`.
- `scripts/migrate_runtime_to_nvme.sh`
  - source root `/mnt/sdb2/home/l4nd0/tenn`, destination `/mnt/nvme/tenn`; likely historical migration script.
- `scripts/archive_prune_root_ollama_store.py`
  - archive path under `/mnt/sdb2/home/l4nd0/tenn/.archives/...`.
- `debug_build_item_500.py` and `debug_session_500.py`
  - `PROJECT_ROOT=/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2`.
- `docs/setup/environment.md`, `docs/architecture/model-routing.md`, `docs/architecture/17_agentic_chat_architecture.md`, `HANDOFF.md`
  - older `/mnt/nvme/tenn/...` runtime/model references and `/mnt/sdb2` archive references.
- `financial-engine_v2/docker-compose.yml`
  - canonical resolved workspace path `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
  - canonical `/mnt/tenn-nvme2` data/report mounts.
  - fallback model mount `${TENN_MODELS_NVME_DIR:-/mnt/nvme/tenn/models}`.
- `scripts/start_config.env`
  - `ENGINE_ROOT=/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2`.
  - `LLAMA_SERVER_BIN=/home/l4nd0/tenn-runtime/...`.
  - `COCKPIT_STATE_DB_ON_STARTUP=/mnt/tenn-nvme2/.../state.db`.
- `scripts/verify_nvme_runtime_endpoints.sh`
  - intentional expected values for canonical resolved path and `/mnt/tenn-nvme2`.

Several docs contain historical absolute `/home/l4nd0/tenn` links. Those are not stale by themselves because `/home/l4nd0/tenn` is the desired operator path.

## Recommended Target Topology

Use this one-path rule for active runtime source:

```text
Operators and agents use /home/l4nd0/tenn as the only active Tenn repo entrypoint.
Runtime launchers may resolve that path to /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1, but service definitions, cron, and automation targets should not point to old HDD or fast-dev checkouts unless the job explicitly says so.
```

Recommended target state:

- Backend, worker, and GPU worker code from canonical `/home/l4nd0/tenn/financial-engine_v2`.
- Backend/worker `/data` and report mounts from `/mnt/tenn-nvme2/tenn/financial-engine_v2/...`.
- Qdrant/Postgres Docker volumes left in place.
- Cockpit UI served from `/home/l4nd0/tenn/cockpit-ui`.
- Nightly news cron served from `/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh` only after canonical newspaper4k venv exists.
- Llama units either use `/home/l4nd0/tenn-runtime` with documentation that it resolves to canonical, or use `/home/l4nd0/tenn` directly after approval.
- Codex automation timers target canonical or are disabled/re-scoped by explicit approval.
- Old `/mnt/sdb2/home/l4nd0/tenn` remains preserve/evidence/git-common-dir only.
- `/home/l4nd0/tenn-fast-dev-storage-v1` remains preserve/evidence until untracked and modified files are reconciled.

## What Breaks If Moved Now

- Backend/workers would lose fast-dev untracked Appendix 5B and extraction evaluation files unless they are first preserved or integrated.
- Container `/data` would switch from fast-dev repo-local data to `/mnt/tenn-nvme2` data. This is probably desired, but it is a runtime data binding change and needs explicit approval.
- Cockpit UI may lose the fast-dev `allowedDevOrigins` change and route type generation tweak.
- Cron would fail from canonical today because the newspaper4k venv is missing there.
- Codex automation timers still target fast-dev; leaving them unchanged after runtime rebind would continue to produce work against the old active code path.
- The repo `systemd/llama-cpp-router.service` template still points to `/mnt/sdb2`, so reinstalling from the repo template without fixing it would regress the installed unit path.

## Proposed Implementation Phases

1. Checkpoint/backup evidence
   - Capture Docker, systemd, cron, mount, git, and fast-dev dirty evidence.
   - Preserve fast-dev tracked diff and untracked file manifest before any rebind.
2. Stop/rebind/start Docker if approved
   - Recreate backend, worker, and gpu_worker from canonical compose.
   - Keep qdrant/postgres volumes unchanged.
   - Confirm container `/data` points to `/mnt/tenn-nvme2`.
3. Rebind Cockpit UI service if approved
   - Preserve fast-dev UI changes or apply intentional canonical equivalent.
   - Replace transient service launch from canonical path.
4. Update cron if approved
   - Build/verify canonical newspaper4k venv.
   - Update crontab to canonical path.
5. Update docs/templates/guardrails
   - Fix stale repo template paths and `storage_guard.py` guidance if code mutation is approved.
   - Document git-common-dir and registry-root confusion.
6. Validation and rollback
   - Validate health, mounts, provenance, service paths, cron dry-run, and rollback commands.

## Proposed Commands - DO NOT RUN IN THIS AUDIT

Evidence checkpoint:

```bash
# DO NOT RUN IN THIS AUDIT
cd /home/l4nd0/tenn
mkdir -p reports/agent_jobs/runtime_topology_reconciliation_impl_v1/
docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}' > reports/agent_jobs/runtime_topology_reconciliation_impl_v1/docker-ps-before.txt
docker inspect fe_backend fe_worker fe_gpu_worker fe_qdrant fe_postgres fe_redis > reports/agent_jobs/runtime_topology_reconciliation_impl_v1/docker-inspect-before.json
systemctl --user show tenn-cockpit-ui-frontend.service llama-cpp-router.service llama-cpp-qwen25.service > reports/agent_jobs/runtime_topology_reconciliation_impl_v1/systemd-before.txt
crontab -l > reports/agent_jobs/runtime_topology_reconciliation_impl_v1/crontab-before.txt
git -C /home/l4nd0/tenn-fast-dev-storage-v1 status --short --untracked-files=all > reports/agent_jobs/runtime_topology_reconciliation_impl_v1/fast-dev-status-before.txt
git -C /home/l4nd0/tenn-fast-dev-storage-v1 diff --binary > reports/agent_jobs/runtime_topology_reconciliation_impl_v1/fast-dev-tracked-before.diff
git -C /home/l4nd0/tenn-fast-dev-storage-v1 ls-files --others --exclude-standard > reports/agent_jobs/runtime_topology_reconciliation_impl_v1/fast-dev-untracked-before.txt
```

Docker rebind:

```bash
# DO NOT RUN IN THIS AUDIT
cd /home/l4nd0/tenn
bash scripts/verify_nvme_runtime_endpoints.sh
cd /home/l4nd0/tenn/financial-engine_v2
export TENN_GIT_HEAD="$(git -C /home/l4nd0/tenn rev-parse HEAD)"
export TENN_GIT_HEAD_SHORT="$(git -C /home/l4nd0/tenn rev-parse --short=12 HEAD)"
export TENN_GIT_BRANCH="$(git -C /home/l4nd0/tenn branch --show-current)"
export TENN_GIT_DIRTY="$(test -z "$(git -C /home/l4nd0/tenn status --short)" && echo false || echo true)"
export TENN_GIT_STATUS_LINE_COUNT="$(git -C /home/l4nd0/tenn status --short | wc -l | tr -d ' ')"
export TENN_BUILD_TIME="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
docker compose --env-file .env.docker -f docker-compose.yml run --rm -T backend alembic upgrade head
docker compose --env-file .env.docker -f docker-compose.yml up -d --build --force-recreate backend worker gpu_worker
```

Cockpit UI rebind:

```bash
# DO NOT RUN IN THIS AUDIT
systemctl --user stop tenn-cockpit-ui-frontend.service
systemd-run --user \
  --unit=tenn-cockpit-ui-frontend \
  --property=WorkingDirectory=/home/l4nd0/tenn/cockpit-ui \
  --setenv=NEXT_PUBLIC_API_URL=http://localhost:8000 \
  /usr/bin/env ./node_modules/.bin/next dev -H 0.0.0.0 -p 3000
systemctl --user show tenn-cockpit-ui-frontend.service -p WorkingDirectory -p ExecStart -p ActiveState
```

Cron rebind:

```bash
# DO NOT RUN IN THIS AUDIT
cd /home/l4nd0/tenn
python3 -m venv integrations/newspaper4k_au/.venv
integrations/newspaper4k_au/.venv/bin/pip install -r integrations/newspaper4k_au/requirements.txt
/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
crontab -l > /tmp/tenn-crontab.before
sed 's#/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh#/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh#' /tmp/tenn-crontab.before > /tmp/tenn-crontab.after
crontab /tmp/tenn-crontab.after
crontab -l
```

Template/docs follow-up:

```bash
# DO NOT RUN IN THIS AUDIT
cd /home/l4nd0/tenn
rg -n '/mnt/sdb2/home/l4nd0/tenn|/home/l4nd0/tenn-fast-dev-storage-v1|/mnt/hdd-data/home/l4nd0/tenn' systemd scripts docs AGENTS.md CLAUDE.md financial-engine_v2/CLAUDE.md
```

## Rollback Plan - DO NOT RUN IN THIS AUDIT

Docker rollback:

```bash
# DO NOT RUN IN THIS AUDIT
cd /home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2
docker compose --env-file .env.docker -f docker-compose.yml up -d --build --force-recreate backend worker gpu_worker
docker inspect fe_backend fe_worker fe_gpu_worker --format '{{.Name}} {{range .Mounts}}{{.Source}}->{{.Destination}} {{end}}'
```

Cockpit UI rollback:

```bash
# DO NOT RUN IN THIS AUDIT
systemctl --user stop tenn-cockpit-ui-frontend.service
systemd-run --user \
  --unit=tenn-cockpit-ui-frontend \
  --property=WorkingDirectory=/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui \
  --setenv=NEXT_PUBLIC_API_URL=http://localhost:8000 \
  /usr/bin/env ./node_modules/.bin/next dev -H 0.0.0.0 -p 3000
```

Cron rollback:

```bash
# DO NOT RUN IN THIS AUDIT
crontab -l > /tmp/tenn-crontab.rollback-before
sed 's#/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh#/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh#' /tmp/tenn-crontab.rollback-before > /tmp/tenn-crontab.rollback-after
crontab /tmp/tenn-crontab.rollback-after
crontab -l
```

## Validation Plan

After approved implementation:

```bash
cd /home/l4nd0/tenn
readlink -f /home/l4nd0/tenn
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
bash scripts/verify_nvme_runtime_endpoints.sh
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
docker inspect fe_backend fe_worker fe_gpu_worker --format '{{.Name}} labels={{index .Config.Labels "com.docker.compose.project.working_dir"}} mounts={{range .Mounts}}{{.Source}}->{{.Destination}} {{end}}'
curl -fsS http://127.0.0.1:8000/api/health
systemctl --user show tenn-cockpit-ui-frontend.service -p WorkingDirectory -p ExecStart -p ActiveState
crontab -l
python3 scripts/agent_job_registry.py list-active
```

Success criteria:

- Backend/worker/gpu_worker labels and bind mounts no longer mention `/home/l4nd0/tenn-fast-dev-storage-v1`.
- Container `/data` is `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`.
- Backend health passes.
- Cockpit UI unit working directory is canonical.
- Cron uses canonical path and a canonical dry-run succeeds.
- Fast-dev worktree remains available as preserve/evidence until explicit retirement.

## Risk Rating

- Current audit risk: LOW, because only task card and report artifacts were written.
- Implementation risk: HIGH.
- Main blockers for implementation:
  - fast-dev has untracked production/evaluation-relevant files absent from canonical;
  - Docker rebind also changes `/data` binding;
  - canonical newspaper4k venv is missing;
  - Codex automation timers still target fast-dev;
  - repo service template and storage guard still carry old path guidance.

User approval is required before any Docker, systemd, cron, symlink, data/report, or runtime binding mutation.

## Project Memory Save Recommendation

Save a memory after approval or explicit user request with:

- canonical `/home/l4nd0/tenn` current HEAD and resolved path;
- Docker backend/workers currently still fast-dev at audit time;
- qdrant/postgres volumes independent of repo path;
- cron still `/mnt/sdb2` because canonical newspaper4k venv is missing;
- fast-dev has Appendix 5B/evaluation untracked work that blocks retirement.

## Audit Validation Results

- `git diff --check`: PASS.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md`: PASS, `ok: true`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md`: PASS while this audit was the only active job.
- `python3 -m json.tool reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/status.json`: PASS before and after registry release.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md`: FAIL as expected due unrelated pre-existing untracked task cards outside this job's allowlist. Output was written to `reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/diff-check.json`.
- `python3 -m json.tool reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/diff-check.json`: PASS.
- Markdown/link checker: SKIPPED because no lightweight `markdownlint`, `markdownlint-cli2`, `markdown-link-check`, or `lychee` command was available on PATH.
- Runtime mutation validation: NOT RUN, by policy.

## Final Git Status

Branch:

```text
migration/clean-runtime-baseline-reconstruct-v1
```

HEAD:

```text
e170f6b255ca4229462d4167861775e82ea3df34
```

`git diff --name-only HEAD` and `git diff --cached --name-only` were empty.

Final `git status --short --untracked-files=all`:

```text
?? docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md
?? docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md
?? docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md
?? docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md
?? docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md
?? docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md
```

The unrelated untracked task cards were not cleaned or modified.

## Registry Release

- `python3 scripts/agent_job_registry.py release runtime_topology_reconciliation_audit_v1_20260522`: PASS.
- Removed active record: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/active/runtime_topology_reconciliation_audit_v1_20260522.json`.
- Final `python3 scripts/agent_job_registry.py list-active`: PASS, `active_jobs: []`.
