---
job_id: strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521
lane: Query Orchestration
owner: Codex
mutation_mode: audit_only
approval_required: false
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521

allowed_files:
  - docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/input_inventory.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/contract_completeness.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/safety_boundary_review.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/artifact_boundary_review.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/gaps_and_risks.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/go_no_go_phase3e.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/diff-check.json
---

# Task

Run Phase 3D Strategy Lab offline adapter contract review only for
QuantDinger/Tenn using the completed Phase 3C offline mock transport bundle.

# Scope

Produce an audit-only contract review and risk decision. This job may read the
Phase 3C report, docs, fixtures, and tests, plus Phase 3B and Phase 2 evidence
only where needed for contract interpretation. It may write only this task card
and the approved report bundle.

# Required Boundaries

- Do not implement a real adapter/client.
- Do not implement real API, MCP, or transport code.
- Do not start QuantDinger, MCP, Docker, Tenn runtime services, or Cockpit.
- Do not issue tokens, add secrets, install dependencies, or edit dependency
  files.
- Do not touch Tenn runtime/backend/product code, Cockpit UI/backend, DB,
  Qdrant, news, memory, financial-truth stores, parser/extraction/gold-label
  files, source-registry files, broker/exchange config, paper/live execution,
  scheduled jobs, or autonomous loops.
- Do not edit `docs/strategy_lab/**` or `tests/strategy_lab/**`; if those docs
  or tests need changes, stop and report that as a Phase 3D finding.
- Treat QuantDinger as a replaceable external read/backtest sidecar/comparator
  only. Tenn remains the research brain, provenance authority, schema validator,
  permission gate, artifact boundary, and review owner.

# Required Preflight

- Print current working directory, repo root, branch, HEAD, git status, worktree
  list, and recent commits.
- Verify whether `/home/l4nd0/tenn` is usable or a symlink to another checkout.
- Verify task-card and registry command help.
- Validate this task card if supported.
- Run registry `list-active` and `check-overlap` if supported.
- Claim the registry job only if no active job or dirty file overlaps this
  task-card/report surface.
- Inspect dirty, untracked, deleted, and staged files.
- Do not clean, stash, reset, remove, unstage, merge, cherry-pick, or modify
  unrelated dirty files.

# Review Scope

Assess whether Phase 3C gives enough specificity for a future separately
approved implementation-plan-only phase across:

- request envelope
- response envelope
- policy decision shape
- audit record shape
- lifecycle states
- allowed operation list
- blocked operation list
- artifact emission decision
- raw payload reference rule
- quarantine decision
- `DATA_MISSING` propagation
- sidecar unavailable and timeout behavior

Verify safety boundaries around no production data access, no Tenn store writes,
no canonical financial truth, no source-registry writes, no credentials or token
issuance, no runtime/Cockpit integration, no real transport, no dependency
installs, and no paper/live/order/bot/kill-switch behavior.

Verify artifact boundaries:

- `strategy_lab_artifact_v1` remains authoritative.
- `strategy_lab_sidecar_artifact_v1` remains pre-envelope only.
- Helper output cannot replace the authoritative envelope.
- Local artifact emission remains pending-review only.
- Only `backtest_run` and `regime_breakdown` are evidence-backed.
- `parameter_sweep`, broad `risk_report`, `factor_test`, and
  `portfolio_experiment` remain default-hold or `DATA_MISSING`.

# Required Outputs

- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/README.md`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/preflight.md`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/input_inventory.md`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/contract_completeness.md`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/safety_boundary_review.md`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/artifact_boundary_review.md`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/gaps_and_risks.md`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/go_no_go_phase3e.md`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/status.json`
- `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/diff-check.json`

# Required Classification

Classify the next safe phase as exactly one of:

- `GO_PHASE3E_OFFLINE_IMPLEMENTATION_PLAN_ONLY`
- `DEFER_CONTRACT_GAPS`
- `DEFER_SCHEMA_OR_POLICY_REVIEW_REQUIRED`
- `REJECT_TOO_RISKY`

If Phase 3E is allowed, it must be implementation-plan-only and must not
implement production adapter/client/store/runtime code.

# Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md --repo-root /home/l4nd0/tenn`
- Claim and later release the registry job if supported and safe.
- Markdown/document sanity check if the repo has one.
- `git diff --check`
- `git diff --cached --check` if staged files exist.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md --repo-root /home/l4nd0/tenn`
- Final `git status --short --untracked-files=all`.
- Prove written files are limited to this task card and the approved report
  bundle.
- Prove no runtime/product code, Tenn stores, `docs/strategy_lab/**`,
  `tests/strategy_lab/**`, production data, services, tokens, dependencies, or
  paper/live execution were touched.

# Definition of Done

- Phase 3D offline adapter contract review report bundle exists.
- Exactly one Phase 3E recommendation is made.
- No real adapter/client, real transport, runtime integration, store write,
  dependency install, token issuance, or paper/live execution happened.
