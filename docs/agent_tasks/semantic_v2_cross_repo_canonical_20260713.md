---
job_id: semantic_v2_cross_repo_canonical_20260713
lane: Reporting
owner: Codex
allowed_files:
  - .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py
  - .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py
  - docs/agent_tasks/semantic_v2_cross_repo_canonical_20260713.md
  - scripts/agent_job_hook.py
  - scripts/test_agent_job_hook.py
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/CODE_REVIEW.md
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/DECISION_ENTRY.json
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/DECISIONS.md
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/PR_REVIEW.md
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/RUN_OUTCOME.json
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/STATE.md
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/VALIDATION.md
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/diff-check.json
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/status.json
  - reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713/validation.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/semantic_v2_cross_repo_canonical_20260713
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
control_contract_version: 2
project_id: tenn
claim_id: semantic_v2_cross_repo_enforcement
proof_question: Do portable preflight and Stop hooks enforce target-repository canonical identity and the sole active target-worktree V2 claim while preserving V1 behavior?
hypothesis_id: selected_target_and_active_v2_registry_enforce_cross_repo_v2_v1_compat
program_track: offline_development
entry_state: cross_repo_guard_and_stop_hook_not_target_aware
target_transition: portable_cross_repo_guard_and_active_v2_hook_enforced
exit_predicate: Cross-repo origin/master guard coverage and active target-worktree V2 hook coverage pass, including missing-outcome blocking, matching closeout acceptance, and legacy V1 silence.
source_class: tenn_portable_guard_and_hook_source
dataset_version: migration_canonical_c18935634cf91d1ef80985bce29be846a601be7a_cross_repo_review_v2
evidence_hash: sha256:39ad7ec0974ce3b513a8877dc3868b0ca84b996e6a7146b4765b357f4484c242
capabilities:
  - READ
  - REPORT_WRITE
  - CODE_EDIT
  - PUBLISH
resume_only_if: Canonical guard source, active-registry selector semantics, or focused cross-repo regression evidence changes after a blocked closeout.
---

# Semantic V2 cross-repository enforcement

Repair two bounded cross-repository enforcement defects and their focused tests:
the portable Git guard must derive canonical identity from the selected target
upstream/base, and a portable Stop hook without an explicit override must select
the sole non-stale active V2 record whose worktree is the target repository.
Legacy V1 shared-registry jobs remain silent. After all declared validation and
review gates pass, this card authorizes one bounded follow-up commit, push, PR,
and merge containing only its allowed files. Do not deploy or mutate runtime,
data, services, timers, production state, or registry pointers.
