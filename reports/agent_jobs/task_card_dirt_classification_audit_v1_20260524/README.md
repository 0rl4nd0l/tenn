# Task-Card Dirt Classification Audit

Generated: 2026-05-24T10:41:05+10:00

Task card: `docs/agent_tasks/task_card_dirt_classification_audit_v1_20260524.md`

## Confirmed

- Symlink chain is as expected:
  - `/home/l4nd0/tenn -> /home/l4nd0/tenn-runtime`
  - `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  - `pwd` when using `/home/l4nd0/tenn`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- HEAD: `e170f6b255ca4229462d4167861775e82ea3df34`.
- HEAD subject: `chore(strategy-lab): merge phase3g evidence into baseline`.
- This task card validates with no issues.
- Registry `list-active` is supported and returned `active_jobs: []`.
- Registry scope is `shared`; repo root is `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `check-overlap` for this card failed on dirty files outside this card's allowlist, but no active overlapping registry job was present.
- All seven requested task-card files are present and untracked.
- Each of the seven requested task-card files has a corresponding report directory.
- No dirty task cards were modified, staged, removed, committed, merged, cherry-picked, or cleaned.

## Inferred

- The seven requested files are not active registry-owned jobs; they are untracked job-control/evidence artifacts left in the shared checkout.
- The Cockpit UI usefulness cards form a superseded chain: final merge attempt -> rerun -> current-head reapply. Current HEAD already contains later Cockpit Useful Now lineage via `7a8c872f feat(reporting): add cockpit home useful now panel`, while the older source commit `2617337678bc82f03024dd06781dc1b52ddf63a9` is not an ancestor of HEAD.
- `canonical_path_mountpoint_audit_v1_20260522`, `fast_dev_preservation_audit_v1_20260524`, and `runtime_topology_reconciliation_audit_v1_20260522` look like recent completed/released audit evidence that should be preserved or explicitly archived, not silently removed.
- `phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521` looks partially superseded by the Phase 3G baseline merge at `e170f6b2`, but it remains useful provenance for why Cockpit task-card dirt blocked earlier Phase 3G work.
- The original fresh-session repo proof can resume only after approved handling of the seven dirty cards plus this new classification card, or from a clean isolated worktree.

## DATA_MISSING

- No owner approval for removal/archive of any dirty card.
- No proof that all report bundles have already been committed elsewhere.
- No full report-body audit beyond task-card metadata, first-page summaries, and available `status.json`/README evidence.
- No registry claim/release was performed.
- No product/runtime/backend/Cockpit files or Tenn data stores were inspected.

## Branch / HEAD

| Field | Value |
| --- | --- |
| Branch | `migration/clean-runtime-baseline-reconstruct-v1` |
| HEAD | `e170f6b255ca4229462d4167861775e82ea3df34` |
| HEAD subject | `chore(strategy-lab): merge phase3g evidence into baseline` |

Relevant commit evidence:

- `e170f6b2 chore(strategy-lab): merge phase3g evidence into baseline`
- `8729c732 fix(reporting): silence cockpit theme hydration warning`
- `7a8c872f feat(reporting): add cockpit home useful now panel`
- `6babc2b8 chore(reporting): preserve cockpit task-card evidence`
- `26173376 feat(reporting): add cockpit home useful now panel` exists on `integrate/cockpit-ui-usefulness-integrate-v1-20260521` but is not an ancestor of current HEAD.

## Registry State

Validation:

```json
{
  "ok": true,
  "issues": [],
  "job_id": "task_card_dirt_classification_audit_v1_20260524",
  "lane": "Reporting"
}
```

`list-active`:

```json
{
  "active_jobs": [],
  "git_common_dir": "/mnt/sdb2/home/l4nd0/tenn/.git",
  "ok": true,
  "registry_root": "/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry",
  "registry_scope": "shared",
  "repo_root": "/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1",
  "warnings": []
}
```

`check-overlap` for this classification card:

```text
FAILED: dirty files outside current task card allowed_files.
No active jobs were listed.
```

The failure is environmental dirty-task-card noise, not an active registry owner collision.

## Exact Dirty Task-Card Statuses

Scoped command: `git status --short --untracked-files=all -- docs/agent_tasks`

```text
?? docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md
?? docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md
?? docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md
?? docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md
?? docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md
?? docs/agent_tasks/fresh_session_repo_state_proof_v1_20260524.md
?? docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md
?? docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md
?? docs/agent_tasks/task_card_dirt_classification_audit_v1_20260524.md
```

The seven requested files are all `??` untracked and present. Two additional untracked task cards are visible: the prior fresh-session repo proof card and this classification card.

## Per-File Classification

| File | Status | Lane | Purpose | Report path | State | Recommended action | Risk if left dirty |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md` | Present, untracked | Evaluation / Repo Hygiene | Audit and harden canonical repo/path/mountpoint guidance. | Exists: README, status, diff-check | Released audit evidence; still relevant because runtime/path split remains a current concern. | Preserve or commit under separate repo-hygiene/evaluation evidence task; remove only after approval and after report preservation is confirmed. | Blocks overlap checks; removing without preservation loses canonical-path/runtime binding evidence. |
| `docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md` | Present, untracked | Reporting / Cockpit | Reapply Useful Now changes on moved canonical HEAD. | Exists: README, status, diff-check | Released; likely completed/superseded by `7a8c872f` now in HEAD. | Preserve with Cockpit task-card evidence or archive/remove after approval if report bundle is sufficient. | Blocks overlap checks; keeping indefinitely confuses active Cockpit ownership. |
| `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md` | Present, untracked | Reporting / Cockpit | Rerun final canonical merge after canonical HEAD moved. | Exists: README, diff-check; no status.json observed. | Superseded by current-head reapply and later HEAD ancestry. | Archive/remove after approval, or preserve with the Cockpit evidence bundle if historical trace is required. | Blocks overlap checks; can mislead agents into rerunning obsolete merge instructions. |
| `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md` | Present, untracked | Reporting / Cockpit | Original final canonical merge attempt for Useful Now commit. | Exists: README, diff-check; no status.json observed. | Superseded by rerun/current-head reapply; historical failed/blocked merge attempt. | Archive/remove after approval, or preserve as historical merge-blocker evidence. | Blocks overlap checks; can imply an old fast-forward path that no longer matches HEAD. |
| `docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md` | Present, untracked | Evaluation / FastDev / Storage | Audit fast-dev work before runtime topology rebind away from fast-dev. | Exists: README, status, validation, diff-check | Recent high-value audit evidence; not stale. Report says runtime rebind remains blocked until fast-dev work is preserved or discarded. | Preserve/commit under separate fast-dev preservation or Evaluation task before any runtime cleanup/rebind. | Blocks overlap checks; removing loses Appendix 5B/runtime rebind preservation map. |
| `docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md` | Present, untracked | Reporting / Phase 3G / Cockpit collision | Audit Cockpit task-card blocker for Phase 3G consolidation. | Exists: README, preflight, blocking classification, unblock options, recommendation, status, diff-check | Completed audit-only evidence; partially superseded by Phase 3G baseline merge at `e170f6b2`, still useful provenance. | Preserve/commit with Strategy Lab/Cockpit collision evidence or archive after approval once baseline proof is accepted. | Blocks overlap checks; removing without preservation loses why Phase 3G was blocked by Cockpit task-card dirt. |
| `docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md` | Present, untracked | Evaluation / Runtime / Repo Hygiene | Audit runtime topology and produce approval-gated reconciliation plan. | Exists: README, status, diff-check | Released audit evidence; still current/high-risk because runtime topology remains split. | Preserve/commit under separate runtime topology/evaluation evidence task; leave alone until approved handling. | Blocks overlap checks; removing loses live runtime binding/rebind risk evidence. |

## Recommended Handling Order

1. Preserve/commit recent active evidence first: `fast_dev_preservation_audit_v1_20260524.md`, `runtime_topology_reconciliation_audit_v1_20260522.md`, and `canonical_path_mountpoint_audit_v1_20260522.md`.
2. Preserve or archive Phase 3G collision provenance: `phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md`.
3. Decide Cockpit Useful Now historical cleanup as one bundle: current-head reapply, final merge rerun, and original final merge task cards. These look superseded by current HEAD and should not remain loose in the shared checkout.
4. Include this classification audit card/report in the same repo-hygiene closeout, because it will otherwise become the next loose task-card blocker for unrelated jobs.
5. After approved handling, rerun `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/fresh_session_repo_state_proof_v1_20260524.md` before resuming the original fresh-session repo proof.

## Collision Risk After Classification

HIGH until approved handling happens.

Reason: the blockers are now classified, and no active registry jobs exist, but the shared checkout still contains at least nine untracked task cards under `docs/agent_tasks`. Any task card whose allowlist does not include these files will continue to fail overlap/diff gates.

## Fresh-Session Repo Proof Resume Status

Conditionally yes, but not yet.

The original fresh-session repo proof can resume after the seven classified dirty task cards are handled and this classification card/report is also preserved or otherwise approved. Alternatively, rerun the repo proof from a clean isolated worktree based on current HEAD.

## `/save` Recommendation

No immediate `/save` is required for this classification artifact. Consider `/save` after GPT chooses and completes the handling path, especially if preserving the fast-dev/runtime-topology findings as future operational guidance.
