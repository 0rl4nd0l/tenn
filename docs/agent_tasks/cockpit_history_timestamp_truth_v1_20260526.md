---
job_id: cockpit_history_timestamp_truth_v1_20260526
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_history_timestamp_truth_v1_20260526.md
  - reports/agent_jobs/cockpit_history_timestamp_truth_v1_20260526/README.md
  - reports/agent_jobs/cockpit_history_timestamp_truth_v1_20260526/status.json
  - reports/agent_jobs/cockpit_history_timestamp_truth_v1_20260526/validation.json
  - reports/agent_jobs/cockpit_history_timestamp_truth_v1_20260526/diff-check.json
  - cockpit-ui/components/cockpit/history/history-screen.tsx
  - cockpit-ui/components/cockpit/history/history-screen.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_history_timestamp_truth_v1_20260526
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit History Timestamp Truth

Safe-extension task for issue #91.

## Lane

Primary lane: Reporting.

## Objective

Stop the Cockpit History screen from presenting document inventory rows without
real execution timestamps as completed jobs that happened just now with zero
duration.

## Scope

Allowed:

- Create this task card and report artifacts.
- Update `cockpit-ui/components/cockpit/history/history-screen.tsx` to preserve
  timestamp truth and distinguish document inventory rows from execution rows.
- Add focused History component tests for document payloads with `published_at`
  but no execution timestamp fields.

Forbidden:

- Do not touch backend schema, production DB, Qdrant, news, memory, extraction,
  parser routing, prompts, gold labels, model/runtime/GPU/service config, or
  unrelated dirty work.
- Do not fabricate execution timestamps, durations, completed job state, or
  source-backed labels.
- Do not change canonical financial truth or retrieval behavior.

## Acceptance Criteria

- Documents without real job execution timestamps are not displayed as `Just now`
  or `0ms` completed jobs.
- History distinguishes document inventory rows from real queue/job execution
  rows, or shows missing execution time as unknown.
- Summary counters do not call document inventory rows `Total Jobs` or
  `Completed` unless backed by execution evidence.
- Regression coverage includes a document payload with `published_at` but no
  execution timestamp fields.
- Existing queue summary behavior remains honest and does not fabricate
  start/duration values.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_history_timestamp_truth_v1_20260526.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_history_timestamp_truth_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_history_timestamp_truth_v1_20260526.md`
- focused History component test
- Playwright `/history` check for no fabricated `Just now` or `0ms` document rows
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_history_timestamp_truth_v1_20260526.md`
- release the registry claim before final report
