---
job_id: strategy_lab_quantdinger_framework_v1_20260520
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/artifact_schema_v1.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/task_card_outlines.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/diff-check.json
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_00_preflight.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_01_tenn_surface_map.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_02_quantdinger_fit.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_03_artifact_contract.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_04_mcp_runtime_policy.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_05_strategy_lab_ux.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_06_autonomous_value_loops.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_07_runtime_compatibility.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_08_implementation_backlog.md
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# Strategy Lab QuantDinger Framework v1

Design a gated Tenn Strategy Lab / QuantDinger integration framework with
milestone checkpoints. This is an audit and design-framework job only.

## Scope

- Evaluate QuantDinger and related quant/factor/risk/portfolio tooling as a
  possible external sidecar, comparator, or research engine for Tenn.
- Preserve Tenn's evidence, provenance, financial-truth, runtime, and
  local-first boundaries.
- Produce checkpoint reports under the approved report bundle.
- Produce a final decision report, artifact schema proposal, runtime/tool policy
  proposal, Strategy Lab UX framework, autonomous value-loop framework, and
  future task-card outlines.

## Boundaries

Do not implement runtime code, UI code, MCP servers, database writes, Qdrant
writes, memory writes, parser changes, extraction prompt changes, financial
truth changes, broker integrations, live trading, paper trading, Docker
startup, service startup, or production data access.

Treat QuantDinger as non-canonical. No Strategy Lab output may become Tenn
financial truth without a separate, approval-gated task card.

## Required Preflight

- Print branch, HEAD, `git status --short --untracked-files=all`, `git worktree
  list`, and recent commits.
- Identify the current repo path/worktree and whether it appears to be the
  active Tenn worktree.
- Check active task marker support.
- Check registry/list-active and check-overlap if supported.
- Check dirty, untracked, and deleted files.
- Stop before non-report writes if active registry/lock or dirty work creates
  HIGH collision risk.

## Required Milestones

- M0: preflight and safety posture.
- M1: current Tenn surface map.
- M2: QuantDinger capability and risk fit.
- M3: Strategy Lab artifact contract plus `artifact_schema_v1.md`.
- M4: MCP/runtime/tool-policy design.
- M5: Cockpit Strategy Lab UX framework.
- M6: autonomous value-loop framework.
- M7: compatibility/runtime/resource plan.
- M8: follow-on implementation roadmap plus `task_card_outlines.md`.
- M9: final decision report in `README.md`.

## Validation

- Validate this task card.
- Run registry list-active and check-overlap.
- Claim the registry only if no overlapping active job is present.
- Run `git diff --check`.
- Run `python3 scripts/agent_job_contract.py check-diff
  docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md` if the
  repo supports it.
- Verify final writes are limited to this task card and the approved report
  bundle.

## Definition of Done

- All milestone checkpoint reports exist, or skipped checkpoints explicitly say
  DATA_MISSING with a reason.
- Final `README.md` exists.
- `artifact_schema_v1.md` exists.
- `task_card_outlines.md` exists.
- No product/runtime code changed.
- No production data touched.
- Final worktree status is reported honestly.
