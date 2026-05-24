# Canonical Path Mountpoint Audit

Job: `canonical_path_mountpoint_audit_v1_20260522`
Lane: Evaluation
Mode: report-only after hard-stop findings
Canonical entrypoint audited: `/home/l4nd0/tenn`

## Decision

Blocked for safe-extension changes. The canonical repo entrypoint is clear, but live runtime bindings are not all using it:

- Active Docker containers `fe_backend`, `fe_worker`, and `fe_gpu_worker` are mounted from `/home/l4nd0/tenn-fast-dev-storage-v1`.
- Active transient user service `tenn-cockpit-ui-frontend.service` runs from `/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui`.
- User crontab still schedules `nightly_news.sh` from `/mnt/sdb2/home/l4nd0/tenn`.

These are hard-stop conditions for this task because fixing them would require runtime/systemd/cron/Docker/data-binding decisions outside the allowed safe documentation lane. No symlinks, mounts, Docker volumes, systemd units, cron entries, runtime bindings, old preserve checkouts, or data/report paths were changed.

## Confirmed Facts

- `pwd` at session start: `/home/l4nd0`.
- `readlink -f /home/l4nd0/tenn`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `readlink -f /home/l4nd0/tenn-runtime`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Symlink chain:
  - `/home/l4nd0/tenn -> /home/l4nd0/tenn-runtime`
  - `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  - `/home/l4nd0/tenn.previous_symlink_target_20260521 -> /mnt/hdd-data/home/l4nd0/tenn`
- Canonical git top-level: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Canonical HEAD: `8729c7329630099465cd2264a63b7c1b83b61a20`.
- Canonical path mount: `/` backed by `/dev/nvme1n1p1`, `ext4`, `rw,relatime,errors=remount-ro`.
- Canonical filesystem capacity: `458G` size, `406G` used, `29G` available, `94%` used.
- `/mnt/tenn-nvme2` is a separate NVMe mount backed by `/dev/nvme0n1p1`, `ext4`, `rw,noatime`.
- `/mnt/sdb2` is backed by `/dev/sdc2`, `ext4`, `rw,relatime`, and `lsblk` reports `ROTA=1`.
- `/mnt/hdd-data` exists only as an empty directory on this host for this audit; `/mnt/hdd-data/home/l4nd0/tenn` does not exist.
- Task card validation passed for `docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md`.
- Registry claim succeeded; active record and registry root resolved under `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`.

## Inferred Facts

- The true canonical active repo entrypoint for new agent work should be `/home/l4nd0/tenn`, not the resolved implementation path typed directly. This keeps agents insulated from future symlink target updates while still forcing live verification.
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` is the current resolved implementation path behind the canonical entrypoint.
- The Git common-dir on `/mnt/sdb2/home/l4nd0/tenn/.git` is an intentional shared-worktree topology or legacy carryover. It is not itself the working tree being edited through `/home/l4nd0/tenn`, but it makes registry/common-dir evidence look like the old preserve path and must be documented before agents rely on registry roots.
- `/home/l4nd0/tenn-fast-dev-storage-v1` is not the canonical active repo entrypoint today, but it is actively serving Docker/backend/UI runtime surfaces. That must be reconciled before a "one true path" rule can be enforced operationally.

## DATA_MISSING

- No approved target was provided for rebinding Docker, cron, or user systemd services from `/home/l4nd0/tenn-fast-dev-storage-v1` or `/mnt/sdb2/home/l4nd0/tenn` to `/home/l4nd0/tenn`.
- No ownership decision was provided for whether the dirty `/home/l4nd0/tenn-fast-dev-storage-v1` runtime checkout should be preserved, merged, retired, or left as the live runtime source.
- The audit did not enumerate every historical path reference under `reports/agent_jobs`; `rg -l` found 436 matching report/doc/task-card files, mostly historical artifacts. The current operational findings above are from live commands, not from those historical reports.
- The audit did not inspect or mutate `/etc/fstab`, Docker volume definitions, installed crontab contents beyond the single read-only `crontab -l` path match, or old HDD preserve checkout contents.

## Path Classification

| Path | Classification | Evidence |
| --- | --- | --- |
| `/home/l4nd0/tenn` | Active canonical entrypoint | Symlink to `/home/l4nd0/tenn-runtime`; resolves to current clean baseline. |
| `/home/l4nd0/tenn-runtime` | Canonical runtime symlink | Resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`. |
| `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` | Current resolved canonical worktree | Git top-level, branch `migration/clean-runtime-baseline-reconstruct-v1`, HEAD `8729c7329630`. |
| `/home/l4nd0/tenn-fast-dev-storage-v1` | Non-canonical but active runtime worktree | Active Docker mounts, transient Cockpit UI service, branch `migration/clean-runtime-baseline-20260517`, HEAD `6c6748fe87e5`, dirty. |
| `/mnt/sdb2/home/l4nd0/tenn` | Preserve/legacy primary Git metadata path; cron-bound old checkout | Worktree branch `preserve/dirty-work-20260430T065748Z`; git common-dir and registry root live here; crontab invokes `nightly_news.sh` here. |
| `/mnt/hdd-data/home/l4nd0/tenn` | Stale/missing old HDD target | Previous symlink target points here, but path does not exist during this audit. |
| `/mnt/tenn-nvme2/tenn` | Runtime data/model/report mount | Separate NVMe mount with data, reports, models, and Docker volume paths. |
| `/mnt/nvme/tenn` | Runtime compatibility directory on root filesystem | Not a separate mount in this audit; `storage_guard.py` warns but accepts because runtime layout exists. |
| `/home/l4nd0/tenn-*` safe/audit/integrate worktrees | Isolated task worktrees | `git worktree list` shows many branch-specific worktrees. Use only when task card/collision rules require. |
| `/mnt/sdb2/home/l4nd0/tenn-*` worktrees | Older preserve-era worktrees | Many remain in `git worktree list`; do not use unless explicitly tasked. |
| `/mnt/hdd-data/home/l4nd0/tenn-*` entries | Stale/prunable registrations | `git worktree list` marks them prunable and their paths are not accessible under `/mnt/hdd-data` now. |
| `/tmp/tenn-*` entries | Temporary/prunable worktrees | Present in worktree metadata; not active canonical targets. |

## Registry and Git Common-Dir

- `git -C /home/l4nd0/tenn rev-parse --git-common-dir`: `/mnt/sdb2/home/l4nd0/tenn/.git`.
- `git -C /home/l4nd0/tenn rev-parse --git-dir`: `/mnt/sdb2/home/l4nd0/tenn/.git/worktrees/tenn-nvme-clean-baseline-reconstruct-v1`.
- `agent_job_registry.py list-active` returned no active jobs before claim.
- `agent_job_registry.py check-overlap docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` returned `ok: true`.
- Registry root after claim: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`.
- This registry root is shared, but its path is surprising because the canonical worktree itself is under `/home/l4nd0`. Future docs should explain that common-dir/registry paths can point at `/mnt/sdb2` even when the active worktree is the NVMe canonical checkout.

## Runtime, Data, and Report Bindings

- `scripts/verify_nvme_runtime_endpoints.sh` passed and confirmed:
  - runtime symlink: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  - data: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`
  - reports: `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports`
  - models: `/mnt/tenn-nvme2/tenn/models`
  - `/data` and `/reports` aliases resolve to the `/mnt/tenn-nvme2` targets.
- Repo runtime config still contains legacy or ambiguous bindings:
  - `scripts/storage_guard.py` defaults `TENN_CANONICAL_ROOT` to `/mnt/sdb2/home/l4nd0/tenn`.
  - `systemd/llama-cpp-router.service` in the repo points to `/mnt/sdb2/home/l4nd0/tenn`, although installed user services now point to `/home/l4nd0/tenn-runtime`.
  - `financial-engine_v2/scripts/nightly_news.sh` has a crontab comment using `/mnt/sdb2/home/l4nd0/tenn/...`.
  - `scripts/migrate_runtime_to_nvme.sh` uses `/mnt/sdb2/home/l4nd0/tenn` as a migration source.
- Live runtime state:
  - Docker `fe_backend`, `fe_worker`, and `fe_gpu_worker` are running from `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/docker-compose.yml`.
  - Docker mounts for those containers use `/home/l4nd0/tenn-fast-dev-storage-v1/...` for `/workspace`, `/app`, `/data`, and report paths.
  - Transient `tenn-cockpit-ui-frontend.service` is active/running with `WorkingDirectory=/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui`.
  - User crontab contains `0 2 * * * /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`.

## Docs, Config, and Scripts with Old or Ambiguous Paths

Current guidance/config surfaces found by `rg` include:

- Agent guidance: `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `.claude/hooks/start_memory_check.py`, `.claude/hooks/stop_memory_reminder.py`, `.claude/monitors/run_monitors.sh`, `.claude/commands/save.md`.
- Runtime/config/scripts: `scripts/storage_guard.py`, `scripts/start_config.env`, `scripts/verify_nvme_runtime_endpoints.sh`, `scripts/migrate_runtime_to_nvme.sh`, `scripts/archive_prune_root_ollama_store.py`, `scripts/run_llama_server.sh`, `scripts/run_extraction_server.sh`, `systemd/llama-cpp-router.service`, `financial-engine_v2/docker-compose.yml`, `financial-engine_v2/scripts/run_local_backend.sh`, `financial-engine_v2/scripts/nightly_news.sh`, `financial-engine_v2/scripts/run_batch_extract.py`, `financial-engine_v2/scripts/monitor_extraction.py`.
- Repo docs with current or historical path guidance: `docs/cloud_workflow.md`, `docs/startup.md`, `docs/setup/environment.md`, `docs/architecture/model-routing.md`, `docs/ops/recovery_reconstruction_integration_manifest.md`, `docs/claude/current-state.md`, `docs/claude/STATE.md`, `docs/superpowers/plans/2026-04-29-watch-youtube-channel-nlp.md`, plus many task cards and historical reports.
- `rg -l` found 436 matching historical files under `docs/agent_tasks`, `docs/superpowers`, `docs/claude`, and `reports/agent_jobs`.

## Guardrail Changes

No guardrail documentation changes were kept.

I briefly drafted small AGENTS/CLAUDE guardrails after confirming the canonical symlink chain, then reverted them after discovering the active Docker/UI/cron bindings above. The final diff has no `AGENTS.md` or `CLAUDE.md` changes.

Final changed files:

- `docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` - created task card.
- `reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/status.json` - registry status artifact, ignored by Git.
- `reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/README.md` - this report, ignored by Git.

No commit was created because the task escalated to report-only.

## Safest One True Path Rule

Future agents should use this rule after the runtime binding blocker is resolved:

1. Enter Tenn through `/home/l4nd0/tenn`.
2. Always verify `readlink -f /home/l4nd0/tenn`, branch, HEAD, status, worktree list, git common-dir, and registry overlap before mutation.
3. Treat `/mnt/sdb2/...` and `/mnt/hdd-data/...` as preserve/evidence-only unless explicitly assigned.
4. Use isolated safe/audit/integrate worktrees only when the task card or collision rules require it.
5. Final active-repo integration should target `/home/l4nd0/tenn`, not direct resolved paths or old mountpoints.
6. If launched from the wrong path, re-run inspection via `git -C /home/l4nd0/tenn ...`; if runtime bindings or expected branch/HEAD/registry evidence conflict, stop and report.

## Validation Commands and Results

Initial validation already run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` - `ok: true`.
- `python3 scripts/agent_job_registry.py list-active` - initially no active jobs, `ok: true`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` - `ok: true`.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` - `ok: true`.
- `python3 scripts/storage_guard.py` - `TENN STORAGE GUARD: OK`, with warning that `/mnt/nvme` is not a separate filesystem mount.
- `bash scripts/verify_nvme_runtime_endpoints.sh` - `NVME_RUNTIME_ENDPOINTS_OK=1`.

Final closeout validation:

- `git diff --check` - passed with no output.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` - `ok: true`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` - `ok: true`; only this audit job was active at the time of the check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` - failed because pre-existing unrelated untracked task cards under `docs/agent_tasks/` are outside the task-card allowlist. They were not modified, cleaned, committed, or absorbed.
- `python3 -m json.tool reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/status.json` - passed.
- `python3 -m json.tool reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/diff-check.json` - passed.
- `python3 scripts/agent_job_registry.py release canonical_path_mountpoint_audit_v1_20260522` - `ok: true`.
- Final `python3 scripts/agent_job_registry.py list-active` - no active jobs, `ok: true`.

Final branch and status:

- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- HEAD: `8729c7329630099465cd2264a63b7c1b83b61a20`.
- `git diff --name-only HEAD` - no tracked diff.
- `git status --short --untracked-files=all` - only untracked task cards are visible; this audit's task card plus nine unrelated pre-existing task-card files.

## Risks and Blockers

- High: active Docker backend/worker/gpu_worker source paths are `/home/l4nd0/tenn-fast-dev-storage-v1`, not `/home/l4nd0/tenn`.
- High: active Cockpit UI transient user service runs from `/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui`.
- High: user crontab invokes `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`.
- Medium: canonical git common-dir and registry root live under `/mnt/sdb2/home/l4nd0/tenn/.git`, which is valid for shared worktree metadata but confusing for future agents.
- Medium: canonical root filesystem is 94% used.
- Medium: `/home/l4nd0/tenn-fast-dev-storage-v1` is dirty while serving live runtime containers.
- Low/medium: many stale/prunable worktree records remain in `git worktree list`; they were not pruned because pruning is forbidden for this task.

## Recommended Next Action

Approval-gated follow-up: create a runtime-topology reconciliation task card that is explicitly allowed to inspect and, if approved, update cron, installed user systemd units, Docker compose launch roots, and runtime binding docs. That task should decide whether `/home/l4nd0/tenn-fast-dev-storage-v1` remains a live runtime target or is retired in favor of `/home/l4nd0/tenn`.

After that runtime decision, a low-risk docs-only guardrail can safely add the canonical path rule to `AGENTS.md`, `CLAUDE.md`, and possibly `docs/entrypoints.md`.

## Project Memory Save Recommendation

Save this audit outcome: `/home/l4nd0/tenn` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` on branch `migration/clean-runtime-baseline-reconstruct-v1` at HEAD `8729c7329630`, but safe guardrail docs were blocked because active Docker/UI runtime surfaces still used `/home/l4nd0/tenn-fast-dev-storage-v1` and cron still used `/mnt/sdb2/home/l4nd0/tenn`.
