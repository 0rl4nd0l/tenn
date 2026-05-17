---
job_id: nvme_hybrid_runtime_data_binding_v1_20260517
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme_hybrid_runtime_data_binding_v1_20260517.md
  - reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/
  - scripts/start_config.env
  - financial-engine_v2/docker-compose.yml
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Implement temporary hybrid runtime data binding:
- NVMe for small/runtime-critical data;
- HDD for large document/PDF stores;
- no destructive moves;
- no full 153G copy.

# Hard boundaries

- Do not delete data.
- Do not destructive-move data.
- Do not copy the full `data/asx/docs` tree.
- Do not copy huge PDF folders unless they are explicitly small enough after measurement.
- Do not mutate DBs, Qdrant, news stores, PDFs, models, caches, memory stores, or gold labels.
- Do not start/restart services unless all binding checks pass and launch smoke is explicitly safe.
- Do not edit files outside allowed_files.
- Do not integrate deferred commits.
- Do not claim final migration complete.

Required preflight:

```bash
cd /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1
date -Iseconds
hostname
whoami
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git log --oneline --decorate -12

python3 scripts/agent_job_registry.py list-active || true
python3 scripts/agent_job_contract.py validate docs/agent_tasks/nvme_hybrid_runtime_data_binding_v1_20260517.md || true
python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/nvme_hybrid_runtime_data_binding_v1_20260517.md || true
python3 scripts/agent_job_registry.py claim docs/agent_tasks/nvme_hybrid_runtime_data_binding_v1_20260517.md || true
```

Hard stop:
If not on migration/clean-runtime-baseline-reconstruct-v1, stop.

Hard stop:
If active jobs conflict or if worktree is dirty outside this task’s allowed files, stop and report.

Phase 1 — Inventory and classify data by size

Measure:

du -h --max-depth=2 /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data | sort -h | tail -120
du -sh /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/reports || true
du -sh /mnt/nvme/tenn/financial-engine_v2/data || true
du -sh /mnt/nvme/tenn/financial-engine_v2/reports || true
df -hT /mnt/nvme /mnt/hdd-data || true

Classify each top-level data folder as:

COPY_TO_NVME_NOW
KEEP_ON_HDD_TEMPORARILY
BIND_FROM_HDD
DEFER_UNTIL_2TB_NVME
UNKNOWN_REQUIRES_REVIEW

Default classification:

COPY_TO_NVME_NOW for small runtime-critical folders.
KEEP_ON_HDD_TEMPORARILY / BIND_FROM_HDD for large PDF/document folders.

Write:

reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/data_tier_inventory.json

Phase 2 — Prepare NVMe runtime target

Ensure these exist:

mkdir -p /mnt/nvme/tenn/financial-engine_v2/data
mkdir -p /mnt/nvme/tenn/financial-engine_v2/reports

Do not delete anything.

Phase 3 — Copy only small runtime-critical data

Do not use --delete.

Copy only small runtime-critical directories if they exist and fit.

Candidate small folders:

ops
cockpit
raw
db_recovery
asx/importance
reports
resource_library

Use safe rsync -aH or rsync -aHAX where supported.

Suggested commands, but verify each source exists first:

SRC=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data
DST=/mnt/nvme/tenn/financial-engine_v2/data

mkdir -p "$DST"

for rel in ops cockpit raw db_recovery resource_library; do
  if [ -e "$SRC/$rel" ]; then
    mkdir -p "$DST/$(dirname "$rel")"
    rsync -aH --info=progress2 "$SRC/$rel/" "$DST/$rel/"
  fi
done

if [ -e "$SRC/asx/importance" ]; then
  mkdir -p "$DST/asx/importance"
  rsync -aH --info=progress2 "$SRC/asx/importance/" "$DST/asx/importance/"
fi

Reports:

rsync -aH --info=progress2 /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/reports/ /mnt/nvme/tenn/financial-engine_v2/reports/

If any candidate folder is unexpectedly huge, skip it and record why.

Write:

reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/copy_results.json

Phase 4 — Handle large document folders without copying

For now, use explicit HDD bind strategy for large document/PDF paths.

Large folders to keep on HDD temporarily:

data/asx/docs
data/extraction_gold_real/pdfs
data/benchmark/pdfs
data/marketindex/pdfs

Choose the safest implementation:

If Docker Compose supports multiple bind mounts into subpaths, bind large HDD directories directly into the container paths.
If symlinks inside the NVMe data tree are safer and compatible with the app, create symlinks only for the large document directories.
If neither is safe, do not change binding; write a launch blocker report.

Preferred non-destructive symlink approach only if app/container will follow symlinks correctly:

DST=/mnt/nvme/tenn/financial-engine_v2/data
SRC=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data

mkdir -p "$DST/asx"
ln -sfn "$SRC/asx/docs" "$DST/asx/docs"

mkdir -p "$DST/extraction_gold_real"
ln -sfn "$SRC/extraction_gold_real/pdfs" "$DST/extraction_gold_real/pdfs"

mkdir -p "$DST/benchmark"
ln -sfn "$SRC/benchmark/pdfs" "$DST/benchmark/pdfs"

mkdir -p "$DST/marketindex"
ln -sfn "$SRC/marketindex/pdfs" "$DST/marketindex/pdfs"

Hard stop:
If symlink behavior through Docker bind mount is uncertain, prefer explicit Docker bind mounts rather than silently assuming.

Write:

reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/large_docs_binding.json

Phase 5 — Update runtime binding config

Inspect:

scripts/start_config.env
financial-engine_v2/docker-compose.yml

Goal:

backend container /data should resolve to:
/mnt/nvme/tenn/financial-engine_v2/data
reports should resolve to:
/mnt/nvme/tenn/financial-engine_v2/reports
large docs should remain accessible from HDD via symlink or explicit bind mounts
avoid sparse worktree-local data
avoid empty DB/Qdrant volumes

If docker-compose currently has:

./data:/data
./reports:/reports

replace with explicit paths:

/mnt/nvme/tenn/financial-engine_v2/data:/data
/mnt/nvme/tenn/financial-engine_v2/reports:/reports

If using explicit large-doc bind mounts, add them carefully, for example:

/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/asx/docs:/data/asx/docs:ro
/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/extraction_gold_real/pdfs:/data/extraction_gold_real/pdfs:ro
/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/benchmark/pdfs:/data/benchmark/pdfs:ro
/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/marketindex/pdfs:/data/marketindex/pdfs:ro

Use :ro for large HDD document folders unless write access is required.

Preserve Postgres/Qdrant named volume names. Do not rename them.

Write:

reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/binding_changes.json

Phase 6 — Validate binding without launching

Run:

grep -R "ENGINE_ROOT\|/data\|./data\|/reports\|./reports\|fe_pgdata\|fe_qdrant" -n scripts/start_config.env financial-engine_v2/docker-compose.yml || true
du -sh /mnt/nvme/tenn/financial-engine_v2/data || true
du -sh /mnt/nvme/tenn/financial-engine_v2/reports || true
find /mnt/nvme/tenn/financial-engine_v2/data -maxdepth 3 -type f | head -50 || true
find /mnt/nvme/tenn/financial-engine_v2/data -maxdepth 4 -type l -ls || true
docker volume inspect financial-engine_v2_fe_pgdata financial-engine_v2_fe_qdrant || true

Check:

/data will not point to sparse worktree-local data.
large document folders are reachable.
Postgres/Qdrant named volumes are preserved.
no empty-volume risk introduced by renamed volumes.

Write:

reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/post_binding_validation.json

Phase 7 — Optional smoke plan only

Do not launch unless all checks are clean and no conflicting services are active.

Write:

reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/launch_smoke_plan.md

Include:

exact backend launch command
exact frontend launch command
ahealth endpoint checks
data-population checks
docs path checks
rollback commands

Phase 8 — Validation

Run:

git diff --check
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/nvme_hybrid_runtime_data_binding_v1_20260517.md || true
git status --short --untracked-files=all

Phase 9 — Commit policy

If:

only runtime-critical small folders were copied;
large docs are bound/read-only or explicitly deferred;
config edits are limited to allowed files;
no empty-volume risk remains unreported;
git diff --check passes;
worktree status is understood;

then commit:

git add docs/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517.md

git add reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/

git add scripts/start_config.env

git add financial-engine_v2/docker-compose.yml


git commit -m "milestone(evaluation): bind hybrid nvme runtime data"

If not safe, do not commit.

Phase 10 — Final report

Required outputs:

reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/README.md
reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/status.json
reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/data_tier_inventory.json
reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/copy_results.json
reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/large_docs_binding.json
reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/binding_changes.json
reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/post_binding_validation.json
reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/launch_smoke_plan.md
reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/rollback_plan.md

README structure:

NVMe Hybrid Runtime Data Binding
Verdict
HYBRID_BINDING_IMPLEMENTED
HYBRID_BINDING_PARTIAL
HYBRID_BINDING_BLOCKED
Branch / HEAD
Data tiering
copied to NVMe
kept on HDD
symlinked or bind-mounted
deferred until 2TB NVMe
Binding changes
scripts/start_config.env
financial-engine_v2/docker-compose.yml
Docker volume safety
Postgres
Qdrant
empty-volume risk
Launch readiness
READY_FOR_LAUNCH_SMOKE
NOT_LAUNCH_READY
DATA_MISSING
Validation results
Rollback plan
Tomorrow 2TB NVMe migration follow-up
what to move later
how to remove temporary HDD binds later
Project Memory save recommendation

Final status.json must include:
{
"job_id": "nvme_hybrid_runtime_data_binding_v1_20260517",
"verdict": "",
"launch_readiness": "",
"branch": "migration/clean-runtime-baseline-reconstruct-v1",
"starting_head": "",
"final_head": "",
"commit_created": false,
"commit_hash": "",
"small_runtime_data_copied": false,
"large_docs_kept_on_hdd": true,
"large_docs_binding_method": "",
"source_data_path": "/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data",
"target_data_path": "/mnt/nvme/tenn/financial-engine_v2/data",
"source_reports_path": "/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/reports",
"target_reports_path": "/mnt/nvme/tenn/financial-engine_v2/reports",
"empty_volume_risk_resolved": false,
"services_restarted": false,
"data_destructive_move_performed": false,
"next_safe_step": ""
}

Before finishing:

git status --short --untracked-files=all
git log --oneline --decorate -12
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/nvme_hybrid_runtime_data_binding_v1_20260517.md || true
python3 scripts/agent_job_registry.py release nvme_hybrid_runtime_data_binding_v1_20260517 || true
