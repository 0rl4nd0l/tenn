---
job_id: preserve_dirty_state_classification_20260512
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/preserve_dirty_state_classification_20260512.md
  - reports/agent_jobs/preserve_dirty_state_classification_20260512/**
approval_required: false
timeout_seconds: 2400
output_dir: reports/agent_jobs/preserve_dirty_state_classification_20260512
mutation_mode: audit_only
production_data_access: false
---

# Task

Classify the current preserve worktree dirty state before any Cockpit Home news snapshot integration or extraction baseline rerun. Do not implement fixes.

Primary lane: Reporting

Supporting lanes: Evaluation, Runtime

Mode: AUDIT ONLY

# Goal

Determine what the dirty files are, which lane owns them, whether they are intentional, stale, risky, or need preservation, and whether they block:

1. Cockpit Home news snapshot source-only integration.
2. Shared-router extraction canonical_core rerun.

# Allowed writes

- `docs/agent_tasks/preserve_dirty_state_classification_20260512.md`
- `reports/agent_jobs/preserve_dirty_state_classification_20260512/**`

# Hard boundaries

- Do not edit source files.
- Do not delete dirty files.
- Do not commit.
- Do not run runtime restarts.
- Do not touch DBs, Qdrant, source PDFs, financial truth, company memory, market memory, or news stores.

# Required preflight

- branch
- HEAD
- `git status --short --untracked-files=all`
- `git worktree list`
- recent commits touching dirty files
- active task card if any
- registry/list-active if available

# Files to classify at minimum

- `scripts/run_llama_server.sh`
- `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md`
- `docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md`
- `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md`
- any other dirty/untracked files present at runtime

# Required report

Write:

- `reports/agent_jobs/preserve_dirty_state_classification_20260512/README.md`

The report must include:

- Confirmed facts
- Inferred facts
- DATA_MISSING
- Dirty file table by lane
- Blockers for Cockpit Home news snapshot integration
- Blockers for extraction canonical_core rerun
- Recommended next safe action
- Final git status

# Final checks

- Run `git status --short --untracked-files=all` at end.
- Run task-card `check-diff` if available.
- Release registry claim if acquired.
