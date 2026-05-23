---
job_id: strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521
lane: Provenance
owner: Codex
mutation_mode: audit_only
approval_required: false
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521

allowed_files:
  - docs/agent_tasks/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/draft_task_card.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/diff-check.json
---

# Strategy Lab Phase 3G Consolidation Execution Task-Card Draft

## Objective

Draft the next task card for Strategy Lab consolidation/save execution using the
Phase 3F report. This job is draft-only. It does not perform consolidation,
file movement, staging, unstaging, committing, copying, archiving, cleanup, or
runtime implementation.

## Scope

This task may read the Phase 3F report bundle and current repository state. It
may write only this draft task card and the Phase 3G draft report bundle.

## Required Boundaries

- Do not merge, cherry-pick, commit, copy, stage, unstage, clean, stash, reset,
  remove, or edit Phase 2/2B/3A/3B/3C/3D/3E/3F files.
- Do not edit `docs/strategy_lab/**` or `tests/strategy_lab/**`.
- Do not modify Tenn runtime/backend/product code, Cockpit code, stores,
  parser/extraction/gold-label files, source-registry files, Docker/systemd/env
  files, dependency files, lockfiles, QuantDinger/MCP runtime directories,
  adapter/client implementation, artifact store implementation, real API client
  code, broker/exchange/paper/live execution configs, or unrelated dirty files.
- Do not start QuantDinger, MCP, Docker, Tenn runtime services, Cockpit, paper
  execution, live execution, or trading execution.
- Do not issue tokens, install dependencies, touch production data, or write
  DB/Qdrant/news/memory/financial-truth stores.

## Required Work

- Re-check current repo root, branch, HEAD, git status, and registry state.
- Validate this draft-only task card if supported.
- Draft a future Phase 3G consolidation execution task card in the report
  bundle, using the Phase 3F future action matrix.
- Include exact future candidate paths to save, force-add, archive, exclude, or
  keep pending review.
- Preserve the architecture boundary: Tenn remains the research brain and
  provenance authority; QuantDinger remains a replaceable sidecar/comparator;
  `strategy_lab_artifact_v1` remains authoritative; helper output remains
  pending-review pre-envelope evidence only.
- Record validation and current environmental warnings.

## Required Outputs

- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/README.md`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/preflight.md`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/draft_task_card.md`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/status.json`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/diff-check.json` if supported

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521.md --repo-root /home/l4nd0/tenn`
- Do not claim if unrelated existing dirty files outside the allowlist block the
  registry overlap check.
- Markdown/document sanity check if available.
- `jq empty` for JSON outputs.
- `git diff --check`
- `git diff --cached --check` if staged files exist.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521.md --repo-root /home/l4nd0/tenn`
- Final `git status --short --untracked-files=all`.
- Prove written files are limited to this task card and this report bundle.

## Definition Of Done

- A future Phase 3G consolidation execution task-card draft exists in the report
  bundle.
- The draft keeps actual consolidation behind explicit user approval.
- No candidate file, runtime file, store, dependency, service, token,
  production-data, or trading surface was touched.
