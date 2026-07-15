---
job_id: v2_codex_apply_patch_bootstrap_integration_v1_20260715
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/v2_codex_apply_patch_bootstrap_integration_v1_20260715.md
  - docs/agent_tasks/v2_codex_apply_patch_bootstrap_compat_v1_20260715.md
  - scripts/agent_job_hook.py
  - scripts/test_agent_job_hook.py
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/STATE.md
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/DECISIONS.md
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/VALIDATION.md
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/PR_REVIEW.md
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/RUN_OUTCOME.json
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/DECISION_ENTRY.json
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/LEDGER_ENTRY.json
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/WAIT_RESULT.json
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/diff-check.json
  - reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715/status.json
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/v2_codex_apply_patch_bootstrap_integration_v1_20260715
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
control_contract_version: 2
project_id: tenn
claim_id: v2_codex_apply_patch_bootstrap_exact_head_integration
proof_question: Can immutable implementation anchor 6b7ba9b5ce43398754dab49f8a49c69c068d1b63 merge with only this scope-bootstrap card added, after exact-head and required-check gates pass?
hypothesis_id: immutable_code_anchor_plus_scope_bootstrap_commit_v1
program_track: offline_development
entry_state: validated_implementation_anchor_not_in_stable_canonical
target_transition: immutable_implementation_anchor_plus_scope_card_merged_into_stable_canonical
exit_predicate: One PR has a clean exact head whose only descendant change after implementation anchor 6b7ba9b5ce43398754dab49f8a49c69c068d1b63 is this integration task card, every required check passes, merge completes without drift, and the clean stable canonical checkout is refreshed through its documented detached path.
source_class: tenn_control_plane_source
dataset_version: source_6b7ba9b5ce43_base_af1b33eb2a5e
evidence_hash: sha256:8054f78980474649fd151aa051ee1ca1106d64b592e22d9bb5a4c70f00c2c525
capabilities:
  - READ
  - REPORT_WRITE
  - PUBLISH
resume_only_if: The immutable implementation anchor, scope-bootstrap commit, target canonical head, PR state, required checks, or mergeability evidence changes after a stop.
---

# V2 Codex raw-string apply_patch bootstrap exact-head integration

Integrate the already validated control-plane repair from source branch
`fix/v2-codex-apply-patch-bootstrap-v1-20260715`. Treat exact commit
`6b7ba9b5ce43398754dab49f8a49c69c068d1b63` as the immutable reviewed
implementation anchor. One descendant scope-bootstrap commit containing only
this integration task card becomes the exact PR head.

This card authorizes validation and one commit of this card only, claim/reclaim,
task-ledger updates, report-local evidence writes, source-branch push, one pull
request, exact-head check wait, issue #510 acceptance-criteria update for the
immutable-code-anchor/scope-bootstrap distinction, merge after every required
gate passes, registry release, and refresh of the clean detached stable
canonical checkout at
`/home/l4nd0/tenn-semantic-anti-loop-v2-canonical` to the merged canonical
commit. It does not authorize any source edit, amend, rebase, reset, stash,
clean, force push, branch/worktree deletion, service/runtime/data mutation, or
mutation of dirty, seed, Greyhound, or unrelated checkouts.

## Required gates

- Validate and claim this V2 card before publish operations.
- Rerun portable Git guard and Git identity checks after claim.
- Verify the implementation anchor remains an ancestor of branch/PR HEAD.
- Verify `scripts/agent_job_hook.py` and `scripts/test_agent_job_hook.py` blob
  identities match the immutable implementation anchor exactly.
- Verify the sole descendant commit contains only this integration task card,
  and bind branch/PR/check/merge gates to that new exact head.
- Reuse an existing matching PR or open exactly one PR to stable canonical.
- Re-run focused hook tests, compile, diff check, task-card diff check, and
  final reviewed-diff comparison without modifying source files.
- Wait for required checks with the repo waiter bound to the exact PR head.
- Stop on drift, conflicts, failed checks, unexpected duplicate work, or a
  dirty/unsafe stable canonical checkout.
- Merge only after live PR state confirms exact head, mergeability, review
  gate, and every required check.
- Add to issue #510 acceptance criteria that a validated implementation commit
  may remain the immutable code anchor while a task-card-only descendant commit
  becomes the publication head, provided ancestry, exact blob identity, and
  single-file scope are proven.
- Refresh stable canonical without touching `/home/l4nd0/tenn` or any other
  dirty, seed, runtime, Greyhound, or unrelated checkout.

## Owner-authorized publication evidence

- Prior decision:
  `v2-codex-apply-patch-bootstrap-integration-20260715-pre-push-tools-missing-v1`.
- The rejected pre-push hook reported these missing local executables:
  `financial-engine_v2/.venv/bin/ruff` and
  `financial-engine_v2/.venv/bin/pytest`.
- Equivalent validation already passed through the documented `uv` path:
  focused raw-string selection `9 passed` and complete hook module
  `160 passed`.
- The owner authorizes `TENN_ALLOW_MISSING_HOOK_TOOLS=1` for exactly one push
  of the publication head produced by this task-card-only commit.
- The authorization forbids persisting that environment variable, installing
  dependencies, modifying `financial-engine_v2/.venv`, or modifying any other
  dependency or runtime surface.
- The publication head is the resulting commit whose direct parent is
  `1a2ee248cd696d048724cc88b39648adb69371a3` and whose only changed file is
  this integration task card.
- The changed authorization evidence is bound into V2 semantic control by
  `evidence_hash` value
  `sha256:8054f78980474649fd151aa051ee1ca1106d64b592e22d9bb5a4c70f00c2c525`.

Issue #510 acceptance criteria must also require pre-push validation to use a
deterministic documented tool environment or emit a safe fallback command when
the hardcoded worktree-local virtual-environment executables are unavailable.

## Docs impact

`DOCS_NOT_REQUIRED`: the reviewed source task card already documents the
compatibility behavior, while this card only governs publication and merge.
