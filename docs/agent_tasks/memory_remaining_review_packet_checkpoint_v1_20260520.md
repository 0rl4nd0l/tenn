---
job_id: memory_remaining_review_packet_checkpoint_v1_20260520
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/memory_remaining_review_packet_checkpoint_v1_20260520
allowed_files:
  - docs/agent_tasks/memory_remaining_review_packet_checkpoint_v1_20260520.md
  - docs/agent_tasks/memory_remaining_review_packet_v1_20260520.md
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/README.md
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/operator_review_packet.md
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/operator_review_rows.csv
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/operator_review_rows.json
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/review_summary.json
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/DATA_MISSING.md
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/no_mutation_attestation.md
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/diff-check.json
  - reports/agent_jobs/memory_remaining_review_packet_v1_20260520/status.json
  - reports/agent_jobs/memory_remaining_review_packet_checkpoint_v1_20260520/
  - reports/agent_jobs/memory_remaining_review_packet_checkpoint_v1_20260520/README.md
  - reports/agent_jobs/memory_remaining_review_packet_checkpoint_v1_20260520/diff-check.json
  - reports/agent_jobs/memory_remaining_review_packet_checkpoint_v1_20260520/status.json
---

# Memory Remaining Review Packet Checkpoint v1

Checkpoint the completed Memory Remaining Review Packet v1 task card and report
artifacts into the active NVMe runtime branch.

## Scope

- Preserve `docs/agent_tasks/memory_remaining_review_packet_v1_20260520.md`.
- Preserve `reports/agent_jobs/memory_remaining_review_packet_v1_20260520/`.
- Write a checkpoint report under
  `reports/agent_jobs/memory_remaining_review_packet_checkpoint_v1_20260520/`.
- Force-add ignored report files only from the two allowed report directories.
- Commit only the allowed task cards and report artifacts after validation.

## Boundaries

Do not perform memory cleanup. Do not open production SQLite, call live routes,
touch DBs, mutate memory stores, edit source code, change runtime config, change
Docker/systemd/env files, touch Qdrant/news/source-registry/model files, or
modify parser/extraction, Cockpit, Evaluation Spine/DuckDB, or A2M/news
retrieval files.

Production data access is false.

## Required Preflight

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git status --short --ignored docs/agent_tasks reports/agent_jobs`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_remaining_review_packet_checkpoint_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_remaining_review_packet_checkpoint_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry only if no overlapping artifact checkpoint or Memory
mutation/cleanup work is active.

## Required Validation

- `jq empty reports/agent_jobs/memory_remaining_review_packet_v1_20260520/*.json`
- Python csv readability check for
  `reports/agent_jobs/memory_remaining_review_packet_v1_20260520/operator_review_rows.csv`
- `git diff --cached --name-status`
- `git diff --cached --stat`
- Allowlist leak check over `git diff --cached --name-only`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/memory_remaining_review_packet_checkpoint_v1_20260520.md`
- `git diff --cached --check`

## Commit

If staged files are exactly the allowed task/report artifacts and validation is
clean, commit with:

`milestone(memory): checkpoint remaining review packet`

After commit, verify new HEAD, final git status, commit stat, registry release,
and final active registry list.
