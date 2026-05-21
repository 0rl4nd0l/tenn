---
job_id: nvme_canonical_tenn_symlink_cutover_v1_20260521
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
production_data_access: false
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/nvme_canonical_tenn_symlink_cutover_v1_20260521
allowed_files:
  - docs/agent_tasks/nvme_canonical_tenn_symlink_cutover_v1_20260521.md
  - reports/agent_jobs/nvme_canonical_tenn_symlink_cutover_v1_20260521/
  - reports/agent_jobs/nvme_canonical_tenn_symlink_cutover_v1_20260521/README.md
  - reports/agent_jobs/nvme_canonical_tenn_symlink_cutover_v1_20260521/status.json
  - reports/agent_jobs/nvme_canonical_tenn_symlink_cutover_v1_20260521/diff-check.json
---

# NVMe Canonical Tenn Symlink Cutover v1

Safely make `/home/l4nd0/tenn` the canonical active Tenn path by pointing it at
the NVMe-backed runtime symlink, while preserving the old HDD checkout as an
explicit preserve/evidence-only path.

## Scope

- Audit the current `/home/l4nd0/tenn`, `/home/l4nd0/tenn-runtime`, and
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` topology.
- Audit active Docker containers, user systemd units, listeners, and related
  Tenn processes without stopping or restarting anything.
- If and only if all safety gates pass, change only the external filesystem
  symlink `/home/l4nd0/tenn` so it points to `/home/l4nd0/tenn-runtime`.
- Preserve the previous symlink target as
  `/home/l4nd0/tenn.previous_symlink_target_20260521`.
- Write the final decision report under the approved output directory.

## Required End State If Safe

- `/home/l4nd0/tenn -> /home/l4nd0/tenn-runtime`
- `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- The old HDD checkout remains untouched and is referenced only as an explicit
  preserve/evidence path, such as `/mnt/hdd-data/home/l4nd0/tenn`.

## Allowed Work

- Create and validate this task card.
- Run read-only topology, Git, Docker, systemd, listener, and process audits.
- Claim, heartbeat, and release the repo-local/shared agent job registry when
  overlap checks are clean.
- Write only report artifacts under
  `reports/agent_jobs/nvme_canonical_tenn_symlink_cutover_v1_20260521/`.
- Change only the external symlink `/home/l4nd0/tenn` after all safety gates
  pass.

## Forbidden

Do not edit source files, runtime config, Docker Compose files, systemd unit
files, environment files, models, logs, DBs, Qdrant stores, news stores, memory
stores, production data, generated runtime data, or active production data.

Do not delete, move, rename, clean, or mutate the HDD checkout. Do not stop,
start, restart, rebuild, or relaunch Docker containers or systemd services.

## Required Preflight

Run and report:

- `pwd`
- `readlink -f /home/l4nd0/tenn || true`
- `ls -ld /home/l4nd0/tenn || true`
- `readlink /home/l4nd0/tenn || true`
- `readlink -f /home/l4nd0/tenn-runtime || true`
- `ls -ld /home/l4nd0/tenn-runtime || true`
- `readlink /home/l4nd0/tenn-runtime || true`
- `ls -ld /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1 || true`
- `git -C /home/l4nd0/tenn-runtime branch --show-current || true`
- `git -C /home/l4nd0/tenn-runtime rev-parse --short=12 HEAD || true`
- `git -C /home/l4nd0/tenn-runtime status --short || true`
- `git -C /home/l4nd0/tenn-runtime worktree list || true`
- `python3 /home/l4nd0/tenn-runtime/scripts/agent_job_contract.py validate /home/l4nd0/tenn-runtime/docs/agent_tasks/nvme_canonical_tenn_symlink_cutover_v1_20260521.md`
- `python3 /home/l4nd0/tenn-runtime/scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 /home/l4nd0/tenn-runtime/scripts/agent_job_registry.py check-overlap /home/l4nd0/tenn-runtime/docs/agent_tasks/nvme_canonical_tenn_symlink_cutover_v1_20260521.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry only if overlap is clean.

## Safety Gates

Proceed with the symlink cutover only if all of these are true:

- `/home/l4nd0/tenn` is a symlink pointing to an unavailable HDD path or known
  old preserve path.
- `/home/l4nd0/tenn-runtime` exists and resolves to
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `/home/l4nd0/tenn-runtime` Git status is clean or only contains known
  task/report artifacts from this task.
- Registry overlap is clean.
- No active process requires the broken `/home/l4nd0/tenn` path as a real
  directory.
- No source/config/data mutation is needed.
- No active service restart is required.

Hard stop if any of these are true:

- `/home/l4nd0/tenn` is a real directory, not a symlink.
- `/home/l4nd0/tenn` contains files that would be hidden by relinking.
- `/home/l4nd0/tenn-runtime` is missing or is not a valid Git checkout.
- `/home/l4nd0/tenn-runtime` does not resolve to the NVMe clean baseline.
- `/home/l4nd0/tenn-runtime` is dirty with source/runtime/data changes.
- Active registry jobs overlap.
- The operation would require deleting or moving HDD data.
- The operation would require Docker, systemd, environment, or config edits.
- The operation would require service restarts.
- The operation would mutate DB, Qdrant, news, memory, model, or data stores.

## Required Report

Write `reports/agent_jobs/nvme_canonical_tenn_symlink_cutover_v1_20260521/README.md`
with:

- Executive verdict: `CUTOVER_DONE`, `CUTOVER_BLOCKED`, or `AUDIT_ONLY`.
- Confirmed facts, inferred facts, and `DATA_MISSING`.
- Before and after symlink target and resolved target.
- Whether `/home/l4nd0/tenn-runtime` resolves to the NVMe clean baseline.
- Branch, HEAD, and status before and after.
- Active process, container, listener, and systemd findings.
- Whether any services were restarted; this must be no.
- Whether any source/config/data files changed; this must be no.
- Whether DB, Qdrant, news, memory, model, or data stores were touched; this
  must be no.
- Rollback command.
- Next recommended launch steps.
- Validation commands and exact results.
- Final Git status.
- Registry release status.
- Project Memory save recommendation.

## Validation

- Validate this task card.
- Run registry list-active and check-overlap.
- Claim the registry only if no overlapping active job is present.
- Run the required preflight, topology audit, dependency audit, and post-cutover
  checks.
- Run `git diff --check`.
- Run `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/nvme_canonical_tenn_symlink_cutover_v1_20260521.md`.
- Release the registry claim.
- Verify final writes are limited to this task card and approved report
  artifacts.

## Definition of Done

Either `/home/l4nd0/tenn` safely points to `/home/l4nd0/tenn-runtime`, which
resolves to the NVMe clean baseline, or the report explains the precise blocker.
No services are restarted. No production data is mutated. No source, config,
runtime, or data files are edited.
