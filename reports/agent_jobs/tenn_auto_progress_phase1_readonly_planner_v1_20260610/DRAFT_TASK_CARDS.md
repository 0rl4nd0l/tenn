# Draft Task Cards

These are draft packets only. They are not active execution contracts until an
owner approves creating the real file and running validation.

## Draft Packet A - Issue #281 Phase 2 Dry Run

```yaml
---
job_id: issue_281_eval_lint_type_gates_task_card_dry_run_v1_20260610
task: "Draft a task card for issue #281 lint/type gate work; do not execute it."
issue: 281
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
status: draft_only
approval_required: true
mutation_mode: report_only
production_data_access: false
allowed_files:
  - reports/agent_jobs/issue_281_eval_lint_type_gates_task_card_dry_run_v1_20260610/README.md
  - reports/agent_jobs/issue_281_eval_lint_type_gates_task_card_dry_run_v1_20260610/TASK_CARD_PACKET.md
  - reports/agent_jobs/issue_281_eval_lint_type_gates_task_card_dry_run_v1_20260610/VALIDATION.md
forbidden_files:
  - financial-engine_v2/**
  - scripts/**
  - pyproject.toml
  - requirements*.txt
  - .github/**
validation:
  - "Refresh issue #281 with gh issue view --json ..."
  - "Refresh registry read-only"
  - "Validate generated packet completeness"
  - "git status --short --untracked-files=all"
hard_stops:
  - "Any request to edit backend/scripts/config instead of only drafting"
  - "Any dependency install"
  - "Any broad test, service start, or runtime validation"
  - "Any commit, push, or GitHub write"
---
```

Proposed Phase 3 task-card shape, if Phase 2 is approved and the verifier
accepts it:

- Narrow objective: add a local lint command and minimal config only.
- Candidate allowed files would likely include `pyproject.toml` or a narrowly
  scoped tooling config plus docs/script entrypoint, but Phase 2 must verify
  existing repo tooling first.
- Execution should remain one issue, one task card, one validation lane.

## Draft Packet B - Issue #234 Report-Only Classification

```yaml
---
job_id: issue_234_diff_check_dirt_classification_packet_v1_20260610
task: "Draft a report-only classification plan for issue #234."
issue: 234
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
status: alternate_draft_only
approval_required: true
mutation_mode: report_only
production_data_access: false
allowed_files:
  - reports/agent_jobs/issue_234_diff_check_dirt_classification_packet_v1_20260610/**
forbidden_files:
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json
  - financial-engine_v2/**
validation:
  - "Refresh issue #234"
  - "Inspect current git status"
  - "Classify ownership without changing the artifact"
hard_stops:
  - "Any request to restore, regenerate, or commit the historical artifact"
---
```
