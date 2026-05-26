---
job_id: codex_nightly_lockup_report_v1_20260526
lane: Reporting
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/codex_nightly_lockup_report_v1_20260526.md
  - reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/**
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/codex_nightly_lockup_report_v1_20260526
mutation_mode: audit_only
production_data_access: false
---

# Codex Nightly Lock-Up Report

Mode detail: report-only design and first-pass nightly closeout protocol.

## Objective

Create a bounded nightly lock-up audit that reviews the day's Tenn work,
classifies branch and task-card hygiene, captures candidate learnings, and
produces a next-day handoff. This task defines and runs the first report-only
version. It must extend the existing local `tenn-codex-*` timer/report stack;
it must not create a second scheduler.

## Lane

- Requested primary lane: Repo Hygiene.
- Validator lane: Reporting, because the task-card validator accepts only the
  canonical Tenn lanes.
- Supporting lanes: Evaluation, Query Orchestration, Memory.

## Allowed Scope

- Inspect current repo state, branch, HEAD, worktrees, recent commits, dirty
  files, active agent jobs, and registry state.
- Inspect today's GitHub issue and PR activity.
- Inspect existing local automation outputs under
  `/home/l4nd0/.codex/automations/tenn`.
- Inspect current user-systemd `tenn-codex-*` timer status read-only.
- Classify parked branches and stale task-card/report artifacts.
- Generate report-only merge recommendations, memory-candidate notes, issue
  follow-ups, and next-day handoff instructions.
- Write only this task card and the declared report bundle.

## Required Outputs

- `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/README.md`
- `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/status.json`
- `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/branch_matrix.json`
- `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/github_activity.json`
- `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/memory_candidates.md`
- `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/next_day_handoff.md`
- `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/diff-check.json`

## Nightly Checklist

1. Record branch, HEAD, dirty status, worktrees, active jobs, and timer health.
2. Summarize commits created since local midnight.
3. Summarize GitHub issues and PRs opened, closed, commented, or linked today.
4. Join task cards to report directories and identify loose or stale artifacts.
5. Classify parked branches as `ready_to_review`, `blocked`, `superseded`,
   `needs_rebase`, `needs_validation`, or `archive_candidate`.
6. Check whether any issue closeout lacks task-card/report/validation evidence.
7. Draft merge recommendations only; do not merge.
8. Draft memory candidates only; do not write Codex memory or Tenn memory.
9. Produce a concise next-day handoff with blockers, top next actions, and
   explicit `DATA_MISSING`.

## Forbidden

- Do not create, install, enable, disable, or edit systemd timers, cron entries,
  GitHub Actions, Codex app automations, or any second scheduler.
- Do not merge, cherry-pick, rebase, reset, stash, delete, prune, or clean
  branches.
- Do not commit product code, runtime config, scheduler config, or report
  artifacts outside the declared report bundle.
- Do not mutate production DBs, Qdrant, news stores, memory stores, source
  registries, canonical financial truth, parser routing, extraction prompts,
  gold labels, model config, GPU config, or live services.
- Do not write Codex memory, project memory, Tenn company memory, market memory,
  user thesis memory, or preference memory. Only produce reviewable memory
  candidates in `memory_candidates.md`.
- Do not close GitHub issues or PRs. If an issue appears closable, report the
  evidence and recommended closeout action.
- Do not touch unrelated dirty files or unrelated task cards.

## Promotion Path

This task is report-only. A later safe-extension task may add one consolidated
summary job inside `/home/l4nd0/tenn-codex-automations-v1-20260516` and the
existing `tenn-codex-*` timer/report family. That later task must still avoid
automatic merges and memory writes unless separately approved.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/codex_nightly_lockup_report_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/codex_nightly_lockup_report_v1_20260526.md --repo-root .`
- JSON validation for generated report JSON artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/codex_nightly_lockup_report_v1_20260526.md`

## Hard Stops

- HIGH collision risk on any file this task would write.
- Any required action would mutate product/runtime/data/memory/scheduler state.
- Any required merge, branch cleanup, or GitHub closeout lacks explicit approval.
- GitHub or registry access is unavailable and cannot be represented as
  `DATA_MISSING`.
- The task would duplicate an existing scheduler or bypass the existing local
  `tenn-codex-*` automation base.
