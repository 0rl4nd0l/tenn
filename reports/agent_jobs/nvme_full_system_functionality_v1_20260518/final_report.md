# NVMe full system functionality report

## Executive verdict

`IMPLEMENTED_AND_VALIDATED`

Tenn's normal runtime path is now normalized to the validated NVMe worktree, data/report/model endpoints are populated on NVMe2, active host runtime defaults point directly at NVMe2 endpoints, backend/frontend/runtime health has validation evidence, and rollback notes/artifacts are present.

Host-root `/data` and `/reports` aliases are not required for normal launch after the final path normalization pass. They remain optional compatibility aliases: if created, they must point to NVMe2; if absent, the verifier warns but does not fail because active host launch paths use explicit `/mnt/tenn-nvme2/...` endpoints and Docker maps those host endpoints into container `/data` and `/reports`.

## Branch / HEAD

- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD before: `a99c1762bb72`
- HEAD after: `a99c1762bb72`
- Commit created: none

## Task card and registry

- Task card: `docs/agent_tasks/nvme_full_system_functionality_v1_20260518.md`
- Contract validate: passed, `ok: true`
- Contract check-diff: passed, `ok: true`
- Registry final state: `active_jobs: []`

## Runtime root

- `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `/home/l4nd0/tenn` was not repointed and still resolves to `/mnt/hdd-data/home/l4nd0/tenn`.

## NVMe2 endpoints

- Data: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`
- Reports: `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports`
- Models: `/mnt/tenn-nvme2/tenn/models`

Validated files/directories include:

- `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/fe_local.db`
- `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs`
- `/mnt/tenn-nvme2/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf`
- `/mnt/tenn-nvme2/tenn/models/gpt-oss-20b-mxfp4.gguf`

## Path normalization performed

Repo/runtime files updated to use NVMe/NVMe2 endpoints:

- `financial-engine_v2/scripts/run_local_backend.sh`
- `financial-engine_v2/scripts/monitor_extraction.py`
- `financial-engine_v2/scripts/run_batch_extract.py`
- `scripts/start_config.env`
- `scripts/run_llama_server.sh`
- `scripts/run_extraction_server.sh`
- `scripts/runtime/m40_known_good_llama_server_qwen25_14b.sh`
- `scripts/runtime/m40_llama_router_8001_conservative.sh`
- `scripts/run_ticker_expansion_batch.py`
- `scripts/verify_nvme_runtime_endpoints.sh`
- Paired script expectation tests under `scripts/`

External user config files updated earlier with backups:

- `/home/l4nd0/.config/tenn/llama-server.env`
- `/home/l4nd0/.config/tenn/llamacpp-presets.ini`

External service files updated earlier with backups:

- `/home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service`
- `/home/l4nd0/.config/systemd/user/llama-cpp-router.service`

## Validation results

Latest endpoint verifier artifact:

- `reports/agent_jobs/nvme_full_system_functionality_v1_20260518/final_completion_audit_current_state.txt`

Final verifier result:

```text
NVME_RUNTIME_ENDPOINTS_OK=1
```

Additional validation evidence:

- Shell syntax checks: passed
- Python syntax checks for touched scripts: passed
- `git diff --check`: passed
- Task contract validate/check-diff: passed
- Backend route parity contract: `2 passed, 5 warnings`
- Route-scoped backend set: `28 passed, 5 warnings`
- Backend health smoke: `/api/health` returned `{"status":"ok"}` during isolated validation
- Frontend HTTP smoke: Next dev server returned `HTTP/1.1 200 OK` during isolated validation
- Router runtime smoke: `/v1/models` returned NVMe2 model paths during bounded validation

## Services and ports after completion

- `llama-cpp-qwen25.service`: inactive
- `llama-cpp-router.service`: inactive
- No listeners found on `:8000`, `:8001`, `:8002`, or `:8081` in the final audit.

Known non-blocking warning left unchanged:

- `llama-cpp-qwen25.service` still logs `Unknown key name 'StartLimitIntervalSec' in section 'Service', ignoring.`

## Optional compatibility aliases

Prepared helper remains available if host-root aliases are desired later:

```bash
sudo /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/nvme_full_system_functionality_v1_20260518/complete_after_sudo_aliases.sh
```

Rollback for that optional alias step:

```bash
sudo /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/nvme_full_system_functionality_v1_20260518/host_alias_rollback_commands.sh
```

## Safety confirmations

- HDD source data was not deleted or rewritten.
- `/home/l4nd0/tenn` was not changed.
- DB/Qdrant/Docker volumes were not recreated.
- News import blocker was not fixed or modified.
- Parser, extraction, gold labels, canonical writes, news stores, memory stores, and source HDD data were not changed.
- No branches or worktrees were deleted or pruned.
- No service started by this task was left running.

## Rollback plan

Runtime symlink rollback:

```bash
rm /home/l4nd0/tenn-runtime
```

Systemd unit rollback:

```bash
cp /home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service.bak.20260518T215550+1000 /home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service
cp /home/l4nd0/.config/systemd/user/llama-cpp-router.service.bak.20260518T215550+1000 /home/l4nd0/.config/systemd/user/llama-cpp-router.service
systemctl --user daemon-reload
```

Model config rollback:

```bash
cp /home/l4nd0/.config/tenn/llama-server.env.bak.20260518T222937+1000 /home/l4nd0/.config/tenn/llama-server.env
cp /home/l4nd0/.config/tenn/llamacpp-presets.ini.bak.20260518T222937+1000 /home/l4nd0/.config/tenn/llamacpp-presets.ini
```

Repo file rollback should be reviewed from the task diff rather than using destructive checkout, because unrelated user work may exist.

## DATA_MISSING

None for required NVMe-root runtime functionality.

Optional compatibility data missing:

- Host-root `/data` alias is absent.
- Host-root `/reports` alias is absent.

## Next safe step recommendation

Commit the allowed task changes after review, or run the optional sudo alias helper if legacy host-root `/data` and `/reports` compatibility is desired.

## Project Memory save recommendation

Save a memory note that `/home/l4nd0/tenn-runtime` is the stable runtime root, `/mnt/tenn-nvme2/tenn/financial-engine_v2/data` and `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports` are the intended data/report endpoints, `/mnt/tenn-nvme2/tenn/models` is the intended model endpoint, and `scripts/verify_nvme_runtime_endpoints.sh` is the read-only proof command.
