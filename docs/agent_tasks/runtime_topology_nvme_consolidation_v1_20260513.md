---
job_id: runtime_topology_nvme_consolidation_v1_20260513
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/runtime_topology_nvme_consolidation_v1_20260513.md
  - reports/agent_jobs/runtime_topology_nvme_consolidation_v1_20260513/
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/runtime_topology_nvme_consolidation_v1_20260513
mutation_mode: audit_only
production_data_access: false
---

# Task

Runtime topology consolidation audit for moving live local Tenn runtime launch base from the HDD preserve worktree to the clean NVMe worktree at `/home/l4nd0/tenn-fast-dev-storage-v1`.

# Goal

Make the live local Tenn runtime clearly serve from `/home/l4nd0/tenn-fast-dev-storage-v1` instead of `/mnt/hdd-data/home/l4nd0/tenn`, without changing product code, databases, Qdrant, embeddings, memory stores, gold labels, model configs, or extraction behavior.

# Mode

Audit first. Safe runtime restart only if every hard gate passes.

# Allowed Writes

- `docs/agent_tasks/runtime_topology_nvme_consolidation_v1_20260513.md`
- `reports/agent_jobs/runtime_topology_nvme_consolidation_v1_20260513/`

# Hard Boundaries

- Do not edit product code.
- Do not edit runtime/model config files.
- Do not touch databases, Qdrant, embeddings, memory stores, gold labels, extraction prompts, or source PDFs.
- Do not start `:8002` unless it is already part of the standard runtime launch and clearly safe.
- Do not change model choice, model path, context size, GPU layers, prompt templates, provider routing, or API keys.
- Do not kill unrelated Codex, Claude, Chorus, or editor processes.
- Do not delete the old HDD worktree.
- Do not clean unrelated task cards.

# Required Report

Write `reports/agent_jobs/runtime_topology_nvme_consolidation_v1_20260513/README.md` with the before/after runtime topology, commands used, health probes, validation, blockers, and next safe step.
