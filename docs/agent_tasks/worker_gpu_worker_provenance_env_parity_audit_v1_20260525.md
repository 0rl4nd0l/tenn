---
job_id: worker_gpu_worker_provenance_env_parity_audit_v1_20260525
lane: Reporting
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/**
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/README.md
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/status.json
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/worker_runtime_inventory.json
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/provenance_gap_register.json
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/recommended_child_task_card.md
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit Tenn worker/runtime environment parity, GPU/runtime provenance, and worker identity/reporting clarity.

This is a Reporting/Ops audit-only task. Do not change runtime configuration, Docker, systemd, cron, GPU allocation, model routing, extraction routing, DB/Qdrant/news stores, memory, financial truth, Cockpit implementation, code, config, or runtime state.

# Scope

Primary lane: Reporting.

Supporting lanes:
- Evaluation
- Provenance

Allowed writes are limited to this task card and report artifacts under:

`reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/`

# Required Preflight

1. Print `pwd`, branch, HEAD, and recent commits.
2. Run `git status --short --untracked-files=all`.
3. Run `git worktree list`.
4. Verify current task-card/registry command syntax from repo help/docs before relying on exact commands.
5. Create or validate this task card.
6. Run registry/list-active if available.
7. Run registry/check-overlap against this task card if available.
8. Confirm whether any active jobs overlap with Reporting, Evaluation, Provenance, worker runtime, GPU/runtime provenance, extraction runtime, or environment-reporting surfaces.
9. Claim this audit job only if no HIGH overlap exists.
10. If overlap exists, stop and write a blocked report only.

# Core Audit Questions

1. What worker/runtime identities currently exist in repo scripts, reports, configs, docs, or service definitions?
2. How is GPU/runtime provenance currently captured for extraction, evaluation, chat, embeddings, and background jobs?
3. Are worker names, runtime URLs, GPU usage, model aliases, and provenance labels consistent across reports and code surfaces?
4. Is there a mismatch between documented worker/runtime expectations and current repo/runtime configuration?
5. Are there stale references to HDD vs NVMe paths, old runtime URLs, APEX/default model aliases, llama.cpp ports, extraction runtime ports, or worker names?
6. Are generated reports clear enough for GPT/Codex to know which runtime produced which artifact?
7. What hardening is needed before production-style personal use?
8. What should be a future implementation task, if any, and what files would be allowed?

# Read-Only Surfaces

Inspect only as needed:
- `docs/agent_tasks/**`
- `reports/agent_jobs/**`
- `financial-engine_v2/docker-compose.yml`
- `financial-engine_v2/backend/**`
- `scripts/**`
- `cockpit-ui/**` only for status/provenance display discovery
- `AGENTS.md`, `CLAUDE.md`, `.codex`, `.claude` settings if present
- runtime/env docs if present
- prior reports referencing GPU/runtime/worker provenance
- current shell environment, read-only
- `nvidia-smi`, process listing, and `docker ps` only if safe and read-only

# Hard Boundaries

- No code edits.
- No config edits.
- No runtime changes.
- No service starts, stops, restarts, rebuilds, reloads, or Docker changes.
- No systemd or cron changes.
- No model routing, GPU routing, parser routing, extraction routing, or scorecard routing changes.
- No extraction, ingestion, backfill, resync, reindex, or production jobs.
- No DB, Qdrant, SQLite, Postgres, news-store, Tenn memory, company memory, market memory, thesis memory, or financial-truth writes.
- Do not touch unrelated dirty files.
- Do not claim runtime parity is fixed.

# Required Outputs

Write:

- `reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/README.md`
- `reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/status.json`
- `reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/worker_runtime_inventory.json`
- `reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/provenance_gap_register.json`
- `reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/recommended_child_task_card.md` only if a safe next implementation is justified

# Validation

Run and report:

- task-card validation if available
- registry/list-active and registry/check-overlap if available
- registry claim/release if supported and safe
- `python3 -m json.tool` for generated JSON artifacts
- `git diff --check`
- task-card `check-diff` if available
- final `git status --short --untracked-files=all`
- final registry/list-active if available

# Decision Policy

- If gaps are report-only/documentation gaps, recommend a bounded Reporting child task.
- If gaps require runtime/env/Docker/systemd/cron changes, do not implement; draft a separate HIGH-risk implementation task requiring explicit approval.
- If active registry collision appears, stop and report blocked.
- If worker/runtime state cannot be proven, mark `DATA_MISSING`.
- If there is no meaningful issue, recommend no-op/defer.
