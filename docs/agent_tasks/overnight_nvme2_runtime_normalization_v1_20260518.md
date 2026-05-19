---
job_id: overnight_nvme2_runtime_normalization_v1_20260518
lane: Reporting
owner: Codex
mutation_mode: safe_extension
production_data_access: false
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 28800
output_dir: reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518
allowed_files:
  - docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md
  - reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/**
  - README.md
  - AGENTS.md
  - CLAUDE.md
  - financial-engine_v2/README.md
  - financial-engine_v2/backend/README.md
  - cockpit-ui/README.md
  - financial-engine_v2/docker-compose.yml
  - financial-engine_v2/docker-compose*.yml
  - financial-engine_v2/.env.example
  - financial-engine_v2/scripts/**
  - scripts/**
---

# Overnight NVMe2 runtime normalization

## Objective

Make Tenn's normal runtime/service root point to the validated NVMe/NVMe2 baseline in a reversible, documented way, then validate enough to prove runtime path correctness.

## Validated target baseline

- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Expected HEAD: `a99c1762bb72`
- Runtime root preference: `/home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

## Guardrails

- Audit first; implement only if the target is unambiguous.
- Do not repoint `/home/l4nd0/tenn` while the user is asleep.
- Do not touch production data, Qdrant, DBs, news stores, memory stores, parser outputs, gold labels, source HDD data, Docker volume contents, Marketplace, or the News loader import blocker.
- External mutation is limited to `/home/l4nd0/tenn-runtime` symlink and inactive user systemd unit path references, with backups and diffs.
- Stop with a blocked report if branch, HEAD, cleanliness, registry overlap, runtime root, service ownership, validation, or rollback safety is not clear.

## Planned stages

1. Preflight and registry lock.
2. Runtime root divergence audit.
3. Reversible symlink/systemd/docs normalization only if safe.
4. Validation and bounded service checks.
5. Final report, status JSON, and registry release.
