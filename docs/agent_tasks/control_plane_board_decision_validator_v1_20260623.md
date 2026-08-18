---
job_id: control_plane_board_decision_validator_v1_20260623
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/control_plane_board_decision_validator_v1_20260623
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/control_plane_board_decision_validator_v1_20260623.md
  - scripts/check_board_decision.py
  - scripts/test_check_board_decision.py
  - docs/dev_flow/templates/BOARD_DECISION.json
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md
  - reports/agent_jobs/control_plane_board_decision_validator_v1_20260623/STATE.md
  - reports/agent_jobs/control_plane_board_decision_validator_v1_20260623/DECISIONS.md
  - reports/agent_jobs/control_plane_board_decision_validator_v1_20260623/VALIDATION.md
  - reports/agent_jobs/control_plane_board_decision_validator_v1_20260623/NEXT_GOAL.md
  - reports/agent_jobs/control_plane_board_decision_validator_v1_20260623/CODE_REVIEW.md
  - reports/agent_jobs/control_plane_board_decision_validator_v1_20260623/diff-check.json
---

# Control Plane Board Decision Validator

## Objective

Implement the narrow control-plane hardening slice recommended by
`reports/agent_jobs/codex_instruction_surface_review_board_v1_20260623/BOARD_DECISION.json`:
add a machine-checkable validator for Tenn `BOARD_DECISION.json` artifacts.

## Scope

- Add one standard-library validator script for board decision JSON.
- Add focused tests for valid decisions, missing required fields, invalid
  decision values, missing minority-objection checks, runtime-proof requirements,
  zoom-out requirements, large/critical authority requirements, and CLI JSON.
- Update the board decision template and minimal operator/status docs so future
  agents know how to run the validator.
- Write report-local closeout artifacts for this implementation.

## Hard Boundaries

- Do not sync host Codex skills.
- Do not mutate Git config, installed Git hooks, GitHub, registry state, live
  ledger state, branches, worktrees, runtime state, product code, data stores,
  extraction code, source PDFs, gold labels, prompts, services, DB, Qdrant,
  Redis, news, memory, model/GPU config, or production data.
- Do not alter `.codex/skills/cockpit-flag-orchestrator`; legacy-surface cleanup
  is a separate owner decision.
- Do not add a new visible repo skill.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_board_decision_validator_v1_20260623.md`
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "BOARD_DECISION.json validator control-plane hardening" --json`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py validate`
- `uv run --with pytest --with pyyaml pytest scripts/test_check_board_decision.py scripts/test_agent_job_contract.py scripts/test_agent_job_hook.py -q`
- `python3 scripts/check_board_decision.py docs/dev_flow/templates/BOARD_DECISION.json --template`
- `python3 scripts/check_board_decision.py reports/agent_jobs/codex_instruction_surface_review_board_v1_20260623/BOARD_DECISION.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_board_decision_validator_v1_20260623.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_board_decision_validator_v1_20260623.md`
- Final `git status --short --untracked-files=all`

## Definition Of Done

- Board decisions have a repo-local validator with structured JSON output and a
  nonzero strict failure path.
- The canonical board decision template passes the validator.
- The triggering board packet passes the validator.
- Focused tests pass.
- Docs identify the validator command.
- Report bundle records preflight, docs impact, validation, risks, unsafe
  actions avoided, and next prompt.
