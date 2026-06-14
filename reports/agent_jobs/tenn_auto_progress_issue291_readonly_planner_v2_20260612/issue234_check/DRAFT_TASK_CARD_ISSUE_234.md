---
job_id: issue_234_dry_run_packet_v1
owner: Codex
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
status: draft_only
approval_required: true
mutation_mode: audit_only
production_data_access: false
output_dir: reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602
allowed_files:
  - docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/README.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/EVIDENCE.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/CLASSIFICATION.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/APPROVAL_PACKET.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/DATA_MISSING.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/VALIDATION.md
timeout_seconds: 3600
---

# Issue 234 Dry-Run Task Card Packet

## Objective

Draft a report-only task-card candidate for issue #234:
`[Repo Hygiene] Classify stale extraction contract parity diff-check dirt`.

## Allowed Actions

- Refresh issue #234 read-only.
- Inspect relevant report/control artifacts needed to classify the issue.
- Write only the task-card and report files listed in `allowed_files`.
- Stop before execution.

## Forbidden Actions

- Do not mutate product, runtime, extraction, data, prompt, source-PDF,
  gold-label, DB, Qdrant, news, memory, service, model/GPU, production-data, or
  live-system files.
- Do not mutate GitHub.
- Do not commit, push, merge, rebase, cherry-pick, reset, stash, clean, delete
  branches, or remove worktrees.

## Validation

- Validate this task card.
- Run read-only registry inspection.
- Run markdown whitespace checks.
- Run `git diff --check`.
- Record final status.
