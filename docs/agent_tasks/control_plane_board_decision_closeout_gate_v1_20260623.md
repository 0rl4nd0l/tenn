---
job_id: control_plane_board_decision_closeout_gate_v1_20260623
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/control_plane_board_decision_closeout_gate_v1_20260623
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md
  - scripts/agent_job_contract.py
  - scripts/test_agent_job_contract.py
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - reports/agent_jobs/control_plane_board_decision_closeout_gate_v1_20260623/STATE.md
  - reports/agent_jobs/control_plane_board_decision_closeout_gate_v1_20260623/DECISIONS.md
  - reports/agent_jobs/control_plane_board_decision_closeout_gate_v1_20260623/VALIDATION.md
  - reports/agent_jobs/control_plane_board_decision_closeout_gate_v1_20260623/NEXT_GOAL.md
  - reports/agent_jobs/control_plane_board_decision_closeout_gate_v1_20260623/CODE_REVIEW.md
  - reports/agent_jobs/control_plane_board_decision_closeout_gate_v1_20260623/diff-check.json
---

# Control Plane Board Decision Closeout Gate

## Objective

Wire the repo-local `BOARD_DECISION.json` validator into task-card closeout so
report bundles containing board decisions are validated automatically by
`python3 scripts/agent_job_contract.py check-closeout <task-card>`.

## Scope

- Detect allowed report artifacts named `BOARD_DECISION.json`.
- Validate each detected board decision using the existing
  `scripts/check_board_decision.py` payload validator.
- Surface board-decision validation failures through the existing closeout JSON
  issue shape.
- Add focused tests for passing and failing board decisions in closeout.
- Update minimal operator/status docs for the automatic closeout gate.
- Preserve a report-local closeout bundle for this implementation.

## Hard Boundaries

- Do not change the board decision schema in this slice.
- Do not change runtime, product, extraction, source PDFs, gold labels, prompts,
  DB, Qdrant, Redis, news stores, memory, model/GPU config, services, or
  production data.
- Do not change GitHub issue state, merge PRs, delete branches, rebase, or
  force-push.
- Do not sync host Codex skills or edit `.codex` surfaces.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md`
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "BOARD_DECISION closeout gate wiring" --json`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py validate`
- `uv run --with pytest --with pyyaml pytest scripts/test_agent_job_contract.py scripts/test_check_board_decision.py scripts/test_agent_job_hook.py -q`
- `python3 scripts/check_board_decision.py docs/dev_flow/templates/BOARD_DECISION.json --template`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/control_plane_board_decision_validator_v1_20260623.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md --repo-root .`

## Definition Of Done

- `check-closeout` fails when an allowed report bundle contains an invalid
  `BOARD_DECISION.json`.
- `check-closeout` passes when a valid board decision is present.
- Existing runtime functionality proof closeout behavior remains covered.
- Docs identify the automatic closeout validation behavior.
- Report bundle records preflight, docs impact, validation, risks, unsafe
  actions avoided, and next prompt.
