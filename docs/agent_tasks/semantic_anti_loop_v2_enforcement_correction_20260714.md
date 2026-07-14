---
job_id: semantic_anti_loop_v2_enforcement_correction_20260714
lane: Reporting
owner: Codex
allowed_files:
  - .codex/hooks.json
  - docs/agent_tasks/semantic_anti_loop_v2_enforcement_correction_20260714.md
  - docs/claude/hooks.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - docs/dev_flow/SEMANTIC_ANTI_LOOP_CONTROL_V2.md
  - scripts/agent_decision_ledger.py
  - scripts/agent_job_contract.py
  - scripts/agent_job_hook.py
  - scripts/agent_job_registry.py
  - scripts/test_agent_decision_ledger.py
  - scripts/test_agent_job_contract.py
  - scripts/test_agent_job_hook.py
  - scripts/test_agent_job_registry.py
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/CODE_REVIEW.md
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/DECISION_ENTRY.json
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/DECISIONS.md
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/PR_REVIEW.md
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/RUN_OUTCOME.json
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/STATE.md
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/VALIDATION.md
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/diff-check.json
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/status.json
  - reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714/validation.json
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/semantic_anti_loop_v2_enforcement_correction_20260714
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
control_contract_version: 2
project_id: tenn
claim_id: semantic_anti_loop_v2_claim_and_closeout_enforcement
proof_question: Can a repository require V2 for non-trivial work without breaking legacy Tenn V1 workflows, task-card bootstrap, or legitimate decision supersession?
hypothesis_id: repo_opt_in_v2_bootstrap_shell_release_and_semantic_replay_v1
program_track: offline_development
entry_state: v2_claim_and_closeout_can_be_bypassed
target_transition: v2_required_repositories_fail_closed_without_breaking_v1
exit_predicate: Semantic replay is rejected under lock, material supersession remains valid, opted-in no-claim mutation and invalid release are blocked, task-card bootstrap and V1 warning compatibility pass, and focused regressions are green.
source_class: tenn_control_plane_source
dataset_version: canonical_ac5a56c1_plus_greyhound_first_five_audit_20260714
evidence_hash: sha256:404fb3c4cb7832c9976799f8ae0aa06dd6fe9b49538f4a7840d41f652192dae1
capabilities:
  - READ
  - REPORT_WRITE
  - CODE_EDIT
  - PUBLISH
resume_only_if: Canonical control-plane source, Greyhound first-five evidence, or focused enforcement regression evidence changes after a blocked closeout.
---

# Semantic Anti-Loop V2 enforcement correction

Correct the bounded enforcement gaps found during the first-five Greyhound
pilot review. Preserve the released dirty draft worktrees as evidence and
implement only in this clean sibling worktree. The change must preserve legacy
V1 warning-compatible workflows, permit a narrow V2 task-card bootstrap, reject
semantic decision replay without forbidding a material superseding decision,
block opted-in no-claim mutations including shell mutations, and require valid
V2 outcome and current-run decision evidence before successful registry release.

This task is control-plane-only. It authorizes the task-registry claim and
release needed for this bounded run plus one reviewed commit, push, pull request,
and merge after validation. It does not authorize product runtime, model,
database, timer, service, production-data, or Greyhound registry mutation.
