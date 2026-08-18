---
job_id: semantic_anti_loop_control_v2_20260713
lane: Reporting
owner: Codex
allowed_files:
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py
  - .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py
  - .agents/skills/tenn-goal-report/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
  - AGENTS.md
  - docs/agent_registry/decision_ledger/README.md
  - docs/agent_tasks/semantic_anti_loop_control_v2_20260713.md
  - docs/claude/hooks.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - docs/dev_flow/SEMANTIC_ANTI_LOOP_CONTROL_V2.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - docs/dev_flow/templates/BOARD_DECISION.json
  - docs/dev_flow/templates/NEXT_GOAL.md
  - scripts/agent_decision_ledger.py
  - scripts/agent_job_contract.py
  - scripts/agent_job_hook.py
  - scripts/agent_job_registry.py
  - scripts/check_board_decision.py
  - scripts/test_agent_decision_ledger.py
  - scripts/test_agent_job_contract.py
  - scripts/test_agent_job_hook.py
  - scripts/test_agent_job_registry.py
  - scripts/test_check_board_decision.py
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/CODE_REVIEW.md
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/DECISION_ENTRY.json
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/DECISIONS.md
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/PR_REVIEW.md
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/RUN_OUTCOME.json
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/STATE.md
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/VALIDATION.md
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/diff-check.json
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/status.json
  - reports/agent_jobs/semantic_anti_loop_control_v2_20260713/validation.json
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/semantic_anti_loop_control_v2_20260713
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
control_contract_version: 2
project_id: tenn
claim_id: semantic_anti_loop_control_v2
proof_question: Can Tenn stop semantically duplicate report-only work while preserving valid offline research and v1 compatibility?
hypothesis_id: control_contract_decision_ledger_outcome_v2
program_track: offline_development
entry_state: v1_task_and_duplicate_control
target_transition: merged_v2_semantic_anti_loop_control
exit_predicate: Focused and regression tests pass, the portable skill is syncable, and the Greyhound pilot can consume the merged contract.
source_class: tenn_control_plane_source
dataset_version: migration_clean_runtime_baseline_871c8566d05c
evidence_hash: sha256:902e6cfb852435dec1b4d49d292ff37b0d04ea82cb08b51d5c0065c835a21388
capabilities:
  - READ
  - REPORT_WRITE
  - CODE_EDIT
  - PUBLISH
resume_only_if: Canonical source or focused validation evidence changes after a blocked closeout.
---

# Semantic Anti-Loop Control V2

Implement the owner-approved Semantic Anti-Loop Control V2 plan in Tenn, preserve legacy v1 workflows with migration warnings, and prepare the merged portable control surface for the Greyhound pilot. This task is control-plane-only and must not mutate product runtime, models, databases, services, timers, production data, or registry pointers.
