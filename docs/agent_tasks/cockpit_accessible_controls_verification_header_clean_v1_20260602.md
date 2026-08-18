---
job_id: cockpit_accessible_controls_verification_header_clean_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md
  - docs/claude/STATE.md
  - cockpit-ui/components/cockpit/verification/verification-header.tsx
  - cockpit-ui/components/cockpit/verification/verification-header.test.tsx
  - reports/agent_jobs/cockpit_accessible_controls_verification_header_clean_v1_20260602/README.md
  - reports/agent_jobs/cockpit_accessible_controls_verification_header_clean_v1_20260602/status.json
  - reports/agent_jobs/cockpit_accessible_controls_verification_header_clean_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_verification_header_clean_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_accessible_controls_verification_header_clean_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_and_pr
related_issue: 53
supersedes_pr: 199
operator_approval_source: "User shifted the active goal to UI-focused Reporting work and requested ongoing closeout with isolated worktrees; current live evidence shows PR #199 carries unrelated extraction files, so this clean replacement keeps the verified UI slice isolated."
---

# Cockpit Accessible Controls: Verification Header Clean Replacement

## Objective

Recreate the narrow issue #53 Verification header accessible-control slice from
`origin/migration/clean-runtime-baseline-reconstruct-v1` without inheriting the
unrelated extraction diff carried by PR #199.

This slice is limited to:

- Active ticker input.
- Method/provider select trigger.
- Strict mode switch.

## Session Declaration

Agent: Codex

Branch: `safe/cockpit-accessible-controls-verification-header-clean-v1-20260602`

Worktree:
`/home/l4nd0/tenn-cockpit-accessible-controls-verification-header-clean-v1-20260602`

Lane: Reporting

Execution mode: SAFE EXTENSION MODE

Intended files: this task card, `verification-header.tsx`, a focused component
test, `docs/claude/STATE.md`, and this report bundle.

Contested surfaces touched: none from AGENTS.md.

Collision risk: LOW. Live duplicate checks found the parent issue #53 and the
polluted PR #199, but no clean replacement branch or PR.

Decision: proceed after validation, active-job check, overlap check, and
registry claim.

## Contract Check

Target system layer: Cockpit client UI only.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.2 Cockpit client role, §1.3
retrieval boundary, and §2 mandatory flow. Backend remains authoritative for all
data and retrieval.

What must not change: backend APIs, extraction, retrieval, memory storage,
financial truth, source/evidence labels, Qdrant/Postgres, runtime/model/GPU
configuration, route behavior, values, handlers, and visible layout.

Why safe: the change only adds durable programmatic names to existing controls
and focused tests prove the names are available through DOM accessibility
queries.

GPU process check required: no. This task does not spawn, restart, or depend on
llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md --repo-root .`
- Focused Verification header component test.
- Targeted ESLint for touched UI files.
- Cockpit UI TypeScript if practical.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_controls_verification_header_clean_v1_20260602.md --repo-root .`
- Registry release and final active-job check.

## Hard Stops

- Exact clean duplicate PR found.
- Active registry overlap on `verification-header.tsx`.
- Proposed fix touches adjacent active Verification route files.
- Backend/data/runtime/memory/extraction changes are required.
- Validation cannot distinguish visual labels from programmatic names.
