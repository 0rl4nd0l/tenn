# Overnight NVMe2 runtime normalization final report

## 1. Executive verdict

PARTIAL_WITH_ROLLBACK_READY

Implemented the reversible runtime-root normalization:

- Created `/home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Updated inactive user systemd llama unit path references only, with backups.
- Ran `systemctl --user daemon-reload`.
- Proved route-scoped backend tests still pass.
- Started the router service only for bounded validation, then stopped it.

The router service start did not stay up. It executed `/home/l4nd0/tenn-runtime/scripts/run_llama_server.sh`, passed the storage guard, then exited with status 1. No retry or flag/model/port/GPU change was attempted.

No commit was made because service validation failed.

## 2. Branch / HEAD before and after

Before:

- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `a99c1762bb72`

After:

- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `a99c1762bb72`

## 3. Task card path and validation status

Task card:

- `docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`

Validation:

- Initial validation failed because `output_dir` was missing.
- User said to ignore that blocker.
- Added `output_dir: reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`: passed.

## 4. Registry claim/release status

- `python3 scripts/agent_job_registry.py list-active`: passed, active jobs `[]`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`: passed.
- `python3 scripts/agent_job_registry.py release docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`: failed because the command expects a job id, not a path.
- `python3 scripts/agent_job_registry.py release overnight_nvme2_runtime_normalization_v1_20260518`: passed.
- Final `list-active`: passed, active jobs `[]`.

## 5. Repo/worktree cleanliness before and after

Before allowed task/report changes:

- Branch and HEAD matched the expected validated baseline.
- Dirty status contained only this task's new task card after card creation.
- Unexpected dirty entries after task/report allowance: `NONE`.

After:

- `git status --short --untracked-files=all` showed the untracked task card only.
- Report artifacts are under `reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/` and are ignored by the repo.
- No commit made.

## 6. Symlink resolution

Before:

- `/home/l4nd0/tenn` -> `/mnt/hdd-data/home/l4nd0/tenn`
- `/home/l4nd0/tenn-runtime` did not exist as a resolved target; `readlink -f` returned `/home/l4nd0/tenn-runtime`.

After:

- `/home/l4nd0/tenn` -> `/mnt/hdd-data/home/l4nd0/tenn`
- `/home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

## 7. Selected runtime root and evidence

Selected runtime root:

- `/home/l4nd0/tenn-runtime`

Evidence:

- Target worktree branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Target worktree HEAD: `a99c1762bb72`
- `/home/l4nd0/tenn-fast-dev-storage-v1` was not selected: it was on `migration/clean-runtime-baseline-20260517`, HEAD `6c6748fe87e5`, and dirty.
- `/home/l4nd0/tenn` and `/mnt/sdb2/home/l4nd0/tenn` were not selected: both resolved to the dirty preserve baseline at HEAD `c102f3f21505`.

## 8. Service state before/after

Before:

- `llama-cpp-qwen25.service`: inactive.
- `llama-cpp-router.service`: inactive.
- No listeners on `:8000`, `:8001`, `:8002`, or `:8081`.

After:

- `llama-cpp-qwen25.service`: inactive.
- `llama-cpp-router.service`: inactive.
- No listeners on `:8000`, `:8001`, `:8002`, or `:8081`.

## 9. Systemd unit before/after paths

`llama-cpp-qwen25.service`:

- Before `WorkingDirectory=/home/l4nd0/tenn`
- After `WorkingDirectory=/home/l4nd0/tenn-runtime`
- Before `ExecStart=/home/l4nd0/tenn/scripts/run_llama_server.sh`
- After `ExecStart=/home/l4nd0/tenn-runtime/scripts/run_llama_server.sh`

`llama-cpp-router.service`:

- Before `RequiresMountsFor=/mnt/sdb2/home/l4nd0/tenn`
- After `RequiresMountsFor=/home/l4nd0/tenn-runtime`
- Before `WorkingDirectory=/mnt/sdb2/home/l4nd0/tenn`
- After `WorkingDirectory=/home/l4nd0/tenn-runtime`
- Before `ExecStart=/mnt/sdb2/home/l4nd0/tenn/scripts/run_llama_server.sh`
- After `ExecStart=/home/l4nd0/tenn-runtime/scripts/run_llama_server.sh`

Exact diffs:

- `reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/systemd_diffs/llama-cpp-qwen25.service.diff`
- `reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/systemd_diffs/llama-cpp-router.service.diff`

## 10. Exact external changes made

Created:

- `/home/l4nd0/tenn-runtime` symlink to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Backed up:

- `reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/systemd_backups/llama-cpp-qwen25.service.before`
- `reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/systemd_backups/llama-cpp-router.service.before`
- `/home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service.bak.20260518T215550+1000`
- `/home/l4nd0/.config/systemd/user/llama-cpp-router.service.bak.20260518T215550+1000`

Edited:

- `/home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service`
- `/home/l4nd0/.config/systemd/user/llama-cpp-router.service`

Ran:

- `systemctl --user daemon-reload`

Not changed:

- `/home/l4nd0/tenn`
- models
- ports
- GPU flags
- DB paths
- Qdrant paths
- Docker volumes
- data/reports bindings

## 11. Exact repo files changed

Created or updated:

- `docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`
- `reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/**`

No product code files were changed.

## 12. Validation commands and exact results

Passed:

- `git diff --check`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md`
- `financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_route_parity_contract.py -q`: `2 passed, 5 warnings`
- `financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_*route* financial-engine_v2/backend/tests/test_route_parity_contract.py -q`: `28 passed, 5 warnings`
- `python3 scripts/agent_job_registry.py release overnight_nvme2_runtime_normalization_v1_20260518`

Failed or partial:

- `systemctl --user start llama-cpp-router.service`: returned success to systemctl start, but service then exited with status 1 and did not remain active.
- Router journal showed the normalized script path executed, storage guard OK, then `Main process exited, code=exited, status=1/FAILURE`.

## 13. Route parity result

Route parity remained healthy:

- Focused route parity: `2 passed, 5 warnings`.
- Route-scoped backend set: `28 passed, 5 warnings`.

## 14. Service start/stop result

Attempted only:

- `llama-cpp-router.service`

Result:

- Service started process from `/home/l4nd0/tenn-runtime/scripts/run_llama_server.sh`.
- Storage guard reported OK.
- Service exited with status 1.
- No port opened on `:8001` or `:8002`.
- Service was stopped after the bounded validation attempt.

Not attempted:

- `llama-cpp-qwen25.service`

Reason:

- Router already proved systemd path resolution reached `/home/l4nd0/tenn-runtime` and then failed inside runtime startup; retrying the sibling service would risk model/GPU churn outside the safe path-normalization objective.

## 15. Ports/processes after completion

Final command:

- `ss -ltnp | grep -E ':8000|:8001|:8002|:8081' || true`

Result:

- No matching listeners.

Final service states:

- `llama-cpp-qwen25.service`: inactive.
- `llama-cpp-router.service`: inactive.

## 16. Confirmations

- HDD source data not touched: confirmed.
- `/data` and `/reports` binding not changed: confirmed.
- DB/Qdrant/Docker volumes not recreated: confirmed.
- News import blocker not fixed: confirmed.
- Marketplace not touched: confirmed.
- `/home/l4nd0/tenn` symlink not changed: confirmed.
- No services left running by this task: confirmed.

## 17. Rollback plan

To restore systemd units:

```bash
cp /home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service.bak.20260518T215550+1000 /home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service
cp /home/l4nd0/.config/systemd/user/llama-cpp-router.service.bak.20260518T215550+1000 /home/l4nd0/.config/systemd/user/llama-cpp-router.service
systemctl --user daemon-reload
```

Equivalent report-local backups:

```bash
cp reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/systemd_backups/llama-cpp-qwen25.service.before /home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service
cp reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/systemd_backups/llama-cpp-router.service.before /home/l4nd0/.config/systemd/user/llama-cpp-router.service
systemctl --user daemon-reload
```

To remove the runtime symlink created by this task:

```bash
[ "$(readlink -f /home/l4nd0/tenn-runtime)" = "/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1" ] && rm /home/l4nd0/tenn-runtime
```

Do not alter `/home/l4nd0/tenn` as part of rollback; it was intentionally left pointing to `/mnt/hdd-data/home/l4nd0/tenn`.

## 18. DATA_MISSING

- Exact router runtime root cause after storage guard OK: missing. Journal showed exit status 1 but not a deeper actionable message in the captured tail.
- qwen25 start validation: intentionally not attempted after router failed.
- Broad `-k route` collection remains intentionally not run because the known News loader import blocker is unrelated and out of scope.

## 19. Next safe step recommendation

Run a new bounded Runtime task to diagnose why `/home/l4nd0/tenn-runtime/scripts/run_llama_server.sh` exits after storage guard OK, without changing model flags or touching data. The first safe check should inspect the script's env/config expectations and compare them against the validated M40 conservative launcher notes before starting GPU-heavy services again.

## 20. Project Memory save recommendation

Save a memory note after user approval:

- On May 18, runtime root normalization created `/home/l4nd0/tenn-runtime` pointing at `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` and path-normalized inactive llama user units. Route parity passed, but bounded `llama-cpp-router.service` validation exited status 1 after storage guard OK, so no commit was made and rollback backups are available.
