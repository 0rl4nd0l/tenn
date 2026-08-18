---
job_id: strategy_lab_readonly_analyst_workflow_v1_20260601
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/strategy_lab_readonly_analyst_workflow_v1_20260601.md
  - cockpit-ui/lib/strategy-lab-review-queue.ts
  - cockpit-ui/lib/strategy-lab-artifacts.test.ts
  - reports/agent_jobs/strategy_lab_readonly_analyst_workflow_v1_20260601/README.md
  - reports/agent_jobs/strategy_lab_readonly_analyst_workflow_v1_20260601/status.json
  - reports/agent_jobs/strategy_lab_readonly_analyst_workflow_v1_20260601/validation.json
  - reports/agent_jobs/strategy_lab_readonly_analyst_workflow_v1_20260601/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_readonly_analyst_workflow_v1_20260601
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
github_mutation_allowed: branch_push_pr_and_issue_comment
related_issue: 76
---

# Strategy Lab Readonly Analyst Workflow

## Objective

Add one analyst-useful Strategy Lab / QuantDinger workflow beyond status/proof
display while preserving repo-only, pending-review, non-live, non-canonical
boundaries.

## Scope

This task is limited to the existing Strategy Lab library response contract and
focused tests. It must not edit Home layout/cards, backend services, runtime
launchers, stores, data, Qdrant, memory, or any live QuantDinger transport.

## Contract Safety

- Target layer: Client/Reporting only.
- Relevant contract: Cockpit remains a client/orchestration layer and must not
  become an authority for financial truth, retrieval, ingestion, memory, or live
  sidecar state.
- Must not change: current_sidecar_available=false, execution_allowed=false,
  canonical_financial_truth=false, real_transport=false, production_data_access=false.
- GPU process check: not required; this task does not spawn, restart, or depend
  on llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_readonly_analyst_workflow_v1_20260601.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_readonly_analyst_workflow_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/strategy_lab_readonly_analyst_workflow_v1_20260601.md --repo-root .`
- focused Strategy Lab artifact Vitest
- focused ESLint on touched frontend files
- JSON validation
- path-redaction scan
- `git diff --check`
- task-card `check-diff`
- registry release before final report

## Hard Stops

- Any Home layout/card edits.
- Any backend/runtime/schema/data mutation.
- Any route that starts, probes, or claims current QuantDinger availability.
- Any result that removes PENDING_REVIEW, DATA_MISSING, or non-canonical flags.
