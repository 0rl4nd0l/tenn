---
job_id: task_card_dirt_hygiene_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md
  - docs/agent_tasks/backend_chat_evidence_guard_canonical_integrate_v1_20260524.md
  - docs/agent_tasks/strategy_lab_status_card_browser_smoke_v1_20260524.md
  - reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/README.md
  - reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/inventory.json
  - reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/inventory.csv
  - reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/status.json
  - reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/task_card_dirt_hygiene_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Task Card Dirt Hygiene

Classify untracked task-card artifacts in the canonical Tenn checkout so future
job checks can distinguish active job evidence from stale coordination dirt.

Scope is limited to task-card metadata and report artifacts. Do not modify
runtime, backend, Cockpit UI, parser, extraction, memory, Qdrant, news, Docker,
cron, topology, dependency, or lockfile surfaces.

The original proposed broad `docs/agent_tasks/*.md` allowance is intentionally
not used in this isolated closeout. Do not delete, move, rename, or rewrite
unrelated task cards. If any task card is owned by an active job, leave it
untouched and classify it as `ACTIVE_CURRENT_TASK_CARD`.

Required outputs:

- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/README.md`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/inventory.json`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/inventory.csv`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/status.json`
- `reports/agent_jobs/task_card_dirt_hygiene_v1_20260524/diff-check.json`

Validation:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`
- `git diff --check`
- JSON validation for generated inventory artifacts
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`
