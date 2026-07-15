---
job_id: v2_codex_apply_patch_bootstrap_compat_v1_20260715
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/v2_codex_apply_patch_bootstrap_compat_v1_20260715.md
  - scripts/agent_job_hook.py
  - scripts/test_agent_job_hook.py
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_compat_v1_20260715/STATE.md
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_compat_v1_20260715/DECISIONS.md
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_compat_v1_20260715/VALIDATION.md
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_compat_v1_20260715/CODE_REVIEW.md
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_compat_v1_20260715/RUN_OUTCOME.json
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_compat_v1_20260715/status.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/v2_codex_apply_patch_bootstrap_compat_v1_20260715
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
control_contract_version: 2
project_id: tenn
claim_id: v2_codex_apply_patch_bootstrap_compatibility
proof_question: Can Codex raw-string apply_patch input bootstrap exactly one task card while every existing patch restriction and mapping-shaped behavior remains unchanged?
hypothesis_id: normalize_raw_apply_patch_to_existing_patch_mapping_v1
program_track: offline_development
entry_state: raw_codex_apply_patch_bootstrap_is_unclassified
target_transition: raw_codex_apply_patch_bootstrap_uses_existing_fail_closed_parser
exit_predicate: Focused raw-string regressions and the complete agent_job_hook test module pass while mapping-shaped payload behavior remains covered.
source_class: tenn_control_plane_source
dataset_version: canonical_af1b33eb2a5e203b
evidence_hash: sha256:de82d5fce67b3181602ed41c29ec514c23f57cb0fce6ea9c491ce9283f5dcb96
capabilities:
  - READ
  - REPORT_WRITE
  - CODE_EDIT
  - PUBLISH
resume_only_if: Canonical hook input shape, Codex apply_patch transport, or focused regression evidence changes after closeout.
---

# V2 Codex free-form apply_patch bootstrap compatibility

## Objective

Normalize raw string `tool_input` only for the `apply_patch` tool so Codex can
bootstrap one task card through the existing V2 admission path.

## Scope

- Preserve mapping-shaped payload behavior.
- Preserve the existing one-file `docs/agent_tasks/*.md` restriction.
- Preserve Add/Update-only admission, Move rejection, repo-relative path
  enforcement, and fail-closed handling for malformed or mixed patches.
- Add regressions for admitted and rejected raw-string payloads.
- Run the focused raw-string regression selection and the complete
  `scripts/test_agent_job_hook.py` suite.
- Produce a local reviewed commit only. No push, pull request, merge, or other
  GitHub mutation is authorized.

## Hard boundaries

- Modify only the two hook files, this task card, and this task's report bundle.
- Do not touch Greyhound databases, units, checkouts, seeds, runtime state, or
  alternate checkouts.
- Do not modify Tenn product/runtime/data/extraction state.
- Do not mutate GitHub, merge, rebase, reset, stash, delete, or clean branches
  or worktrees.

## Required validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/v2_codex_apply_patch_bootstrap_compat_v1_20260715.md`
- Portable Git guard preflight with this task card.
- Focused raw-string `apply_patch` bootstrap regression selection.
- `uv run --no-project --with pytest --with pyyaml pytest -q -p no:cacheprovider scripts/test_agent_job_hook.py`
- `python3 -m py_compile scripts/agent_job_hook.py scripts/test_agent_job_hook.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/v2_codex_apply_patch_bootstrap_compat_v1_20260715.md --repo-root . --no-write-report`

## Definition of done

- Raw-string single-card Add/Update bootstrap is admitted.
- Raw-string mixed, malformed, moved, delete, absolute/outside-repo, and
  non-card patches remain blocked.
- Existing mapping-shaped bootstrap and rejection coverage remains green.
- Focused and full hook tests pass from the clean task worktree.
- The stable canonical checkout remains unchanged and clean.
