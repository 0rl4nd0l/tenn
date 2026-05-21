# NVMe Canonical Tenn Symlink Cutover v1

## Executive Verdict

`CUTOVER_DONE`

`/home/l4nd0/tenn` now points to `/home/l4nd0/tenn-runtime`, and
`/home/l4nd0/tenn-runtime` resolves to the NVMe clean baseline:
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.

No services were restarted. No source, Docker, systemd, env, runtime config,
DB, Qdrant, news, memory, model, or data-store files were edited.

## Confirmed Facts

- Task card validation passed for
  `docs/agent_tasks/nvme_canonical_tenn_symlink_cutover_v1_20260521.md`.
- Initial registry overlap was blocked by
  `post_nvme_next_work_orchestrator_v1_20260521`; a later live recheck returned
  `ok: true` and the task was claimed successfully.
- Before cutover, `/home/l4nd0/tenn` was a broken symlink:
  `/home/l4nd0/tenn -> /mnt/hdd-data/home/l4nd0/tenn`.
- Before cutover, `readlink -f /home/l4nd0/tenn` returned no resolved path.
- Before cutover, `/home/l4nd0/tenn-runtime` resolved to
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- The runtime worktree branch was
  `migration/clean-runtime-baseline-reconstruct-v1`.
- The runtime worktree HEAD was `76042591ab19`.
- Runtime Git status before cutover had only this task card visible:
  `?? docs/agent_tasks/nvme_canonical_tenn_symlink_cutover_v1_20260521.md`.
- Post-cutover, `/home/l4nd0/tenn` target is `/home/l4nd0/tenn-runtime`.
- Post-cutover, `/home/l4nd0/tenn` resolves to
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Backup marker was created:
  `/home/l4nd0/tenn.previous_symlink_target_20260521 -> /mnt/hdd-data/home/l4nd0/tenn`.
- Registry release succeeded:
  `removed_active_record=/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/active/nvme_canonical_tenn_symlink_cutover_v1_20260521.json`.

## Inferred Facts

- Existing running Docker containers had already resolved their bind mounts at
  container start. Changing `/home/l4nd0/tenn` does not change those running
  mounts until a future container restart or launch.
- Future tools and agents that open `/home/l4nd0/tenn` will now enter the NVMe
  runtime symlink path.
- Inactive llama user services already reference `/home/l4nd0/tenn-runtime`.

## DATA_MISSING

- No runtime smoke was run, by instruction.
- No service restart was performed, so future restart behavior was not exercised.
- This audit did not inspect every possible shell alias, cron entry, or external
  launcher outside the requested Docker/systemd/process checks.

## Symlink State

Before:

- `/home/l4nd0/tenn` target: `/mnt/hdd-data/home/l4nd0/tenn`
- `/home/l4nd0/tenn` resolved target: none
- `/home/l4nd0/tenn-runtime` target:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `/home/l4nd0/tenn-runtime` resolved target:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

After:

- `/home/l4nd0/tenn` target: `/home/l4nd0/tenn-runtime`
- `/home/l4nd0/tenn` resolved target:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `/home/l4nd0/tenn-runtime` target:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `/home/l4nd0/tenn-runtime` resolved target:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Rollback command:

```bash
ln -sfn /mnt/hdd-data/home/l4nd0/tenn /home/l4nd0/tenn
```

## Active Runtime Findings

- Running containers: `fe_backend`, `fe_worker`, `fe_gpu_worker`, `fe_qdrant`,
  `fe_postgres`.
- `fe_backend`, `fe_worker`, and `fe_gpu_worker` bind mounts point at
  `/home/l4nd0/tenn-fast-dev-storage-v1` paths, not `/home/l4nd0/tenn`.
- `fe_qdrant` uses
  `/mnt/nvme/docker/volumes/financial-engine_v2_fe_qdrant/_data`.
- `fe_postgres` uses
  `/mnt/nvme/docker/volumes/financial-engine_v2_fe_pgdata/_data`.
- `tenn-cockpit-ui-frontend.service` is active from
  `/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui`.
- `llama-cpp-qwen25.service` and `llama-cpp-router.service` are inactive and
  configured for `/home/l4nd0/tenn-runtime`.
- Listeners found: `0.0.0.0:3000`, `0.0.0.0:6333`, `0.0.0.0:8000`.
- Precise `/proc/*/cwd` scan found no process with cwd at `/home/l4nd0/tenn`,
  under `/home/l4nd0/tenn/`, at `/mnt/hdd-data/home/l4nd0/tenn`, or under that
  old HDD path.

## Validation Commands And Results

- `pwd`: `/home/l4nd0`
- `python3 scripts/agent_job_contract.py validate ...`: `ok: true`
- Initial `python3 scripts/agent_job_registry.py check-overlap ...`: `ok: false`
  due active Evaluation lane overlap.
- Later `python3 scripts/agent_job_registry.py check-overlap ...`: `ok: true`
  with no active jobs.
- `python3 scripts/agent_job_registry.py claim ...`: `ok: true`
- `test -L /home/l4nd0/tenn`: passed.
- Cutover command sequence completed:
  `ln -sfn "$before_target" /home/l4nd0/tenn.previous_symlink_target_20260521`
  and `ln -sfn /home/l4nd0/tenn-runtime /home/l4nd0/tenn`.
- Post-cutover `readlink /home/l4nd0/tenn`: `/home/l4nd0/tenn-runtime`
- Post-cutover `readlink -f /home/l4nd0/tenn`:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Post-cutover `git -C /home/l4nd0/tenn branch --show-current`:
  `migration/clean-runtime-baseline-reconstruct-v1`
- Post-cutover `git -C /home/l4nd0/tenn rev-parse --short=12 HEAD`:
  `76042591ab19`
- Post-cutover `git -C /home/l4nd0/tenn status --short`:
  `?? docs/agent_tasks/nvme_canonical_tenn_symlink_cutover_v1_20260521.md`
- `python3 scripts/agent_job_registry.py release ...`: `ok: true`

## Final Status

- Services restarted: no.
- Source/config/data files changed: no.
- DB/Qdrant/news/memory/model/data stores touched: no.
- HDD checkout deleted, moved, renamed, or mutated: no.
- Symlink changed: yes, `/home/l4nd0/tenn` only.
- Backup marker created: yes,
  `/home/l4nd0/tenn.previous_symlink_target_20260521`.
- Registry release status: `ok: true`.
- Artifact checkpoint committed: yes, task/report artifacts only.
- Final post-checkpoint `git status --short`: clean, no output.
- Project Memory save recommendation: yes. Save that `/home/l4nd0/tenn` is now
  the canonical NVMe-backed runtime symlink and the old HDD target is preserved
  by explicit backup marker and path reference only.

## Next Recommended Launch Steps

- Do not restart services merely for this cutover.
- For any future Docker/systemd relaunch, decide explicitly whether that service
  should continue using `/home/l4nd0/tenn-fast-dev-storage-v1` or move to the
  canonical `/home/l4nd0/tenn` path.
- Keep `/home/l4nd0/tenn.previous_symlink_target_20260521` until an operator
  explicitly decides it is no longer useful.
