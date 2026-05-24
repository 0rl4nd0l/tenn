# Post QuantDinger Milestone Dirt Hygiene Audit

Generated: 2026-05-24T09:36:00Z

## Verdict

The stop-hook milestone dirt warning is reproduced and classified as a task-card
contract/diff hygiene block, not an active registry overlap.

Before this audit card was created, the current worktree had six untracked task
cards. After creating this audit card, the worktree has seven untracked task
cards. The hook blocks because six foreign task cards are outside the active
card allowlist.

No unrelated files were modified, staged, committed, deleted, stashed, reset,
moved, renamed, or formatted.

## Repo State

- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `0973349937cd42d25d9ea72882d1bd7fc787ce07`
- HEAD subject: `milestone(query): show cockpit chat evidence gaps`
- Task card: `docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md`
- Output dir: `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524`

## Registry State

`python3 scripts/agent_job_registry.py list-active --repo-root .` returned:

- `ok: true`
- `active_jobs: []`
- registry root: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`
- registry scope: `shared`

`check-overlap` for this audit returned `ok: false`, but only because existing
dirty files sit outside this audit card's `allowed_files`. There was no active
job overlap involving this audit's allowed files.

## Hook Output

- No active task card: `python3 scripts/agent_job_hook.py` returned `{}`.
- Tracked QuantDinger smoke plan card:
  `TENN_AGENT_TASK_CARD=docs/agent_tasks/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524.md python3 scripts/agent_job_hook.py --platform gemini --event BeforeTool`
  returned a block because the current dirty task cards are outside that card's
  allowlist. The no-write mode was used because the default Stop hook would
  write that card's `diff-check.json` outside this audit's allowed files.
- This audit card:
  `TENN_AGENT_TASK_CARD=docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md python3 scripts/agent_job_hook.py`
  returned a block because six foreign task cards are outside this audit
  allowlist. It wrote only this audit's `diff-check.json`.

Hook classification: expected contract block until foreign task-card dirt is
resolved by owner-specific preservation, archive, or execution tasks.

## Dirty Inventory

Current `git status --short --untracked-files=all` inventory after creating
this audit card:

| Status | Path | Classification | Recommendation |
| --- | --- | --- | --- |
| `??` | `docs/agent_tasks/chat_guard_canonical_review_and_csl_live_smoke_v1_20260524.md` | Query Orchestration report bundle, foreign dirt | Owner review, then separate preservation or archive task |
| `??` | `docs/agent_tasks/disk_pressure_safe_cleanup_audit_v1_20260524.md` | Evaluation/Repo Hygiene audit bundle, foreign dirt | Owner review, then separate preservation or archive task |
| `??` | `docs/agent_tasks/docker_builder_cache_broad_prune_v1_20260524.md` | Evaluation/Runtime safe-extension evidence, foreign dirt | Owner review required; prune output exists but README/status are missing |
| `??` | `docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md` | This audit | Leave uncommitted unless explicitly requested |
| `??` | `docs/agent_tasks/strategy_lab_artifact_review_integration_readiness_v1_20260524.md` | Reporting readiness bundle, stale/foreign dirt | Owner review, preserve or archive as stale readiness evidence |
| `??` | `docs/agent_tasks/strategy_lab_quantdinger_complete_and_next_phases_v1_20260524.md` | QuantDinger-related partial milestone bundle | Best first candidate for separate exact preservation commit or archive decision |
| `??` | `docs/agent_tasks/strategy_lab_quantdinger_readonly_sidecar_online_v1_20260524.md` | QuantDinger-related draft/unexecuted parent card | Owner review: execute as next task or archive under a separate card |

Full per-file evidence is in `file_classification.json`.

## Report Directories

Matching report directories exist and are ignored for five foreign cards:

- `reports/agent_jobs/chat_guard_canonical_review_and_csl_live_smoke_v1_20260524/`
- `reports/agent_jobs/disk_pressure_safe_cleanup_audit_v1_20260524/`
- `reports/agent_jobs/docker_builder_cache_broad_prune_v1_20260524/`
- `reports/agent_jobs/strategy_lab_artifact_review_integration_readiness_v1_20260524/`
- `reports/agent_jobs/strategy_lab_quantdinger_complete_and_next_phases_v1_20260524/`

The matching report directory for
`strategy_lab_quantdinger_readonly_sidecar_online_v1_20260524` is absent.

`git status --short --ignored --untracked-files=all` shows those report files as
`!!` ignored. `git ls-files` and `git log --all -- <path>` found no tracked or
committed versions of the dirty task-card paths or their current report bundles.

## Merge Parking

Merge-parking registry support is absent:

- `docs/agent_registry/merge_parking/REGISTRY.md`: absent
- `docs/agent_registry/merge_parking/parked/`: absent

No merge-parking files were created.

## Files Intentionally Not Touched

All six foreign task cards and their matching report directories were read-only
inspected only. No staging, cleanup, deletion, archive, move, rename, reset,
stash, or formatting was performed.

## DATA_MISSING

- The exact two truncated filenames from the pasted original warning remain
  `DATA_MISSING`; current evidence identifies the two additional current
  foreign task cards as `chat_guard_canonical_review_and_csl_live_smoke...` and
  `docker_builder_cache_broad_prune...`.
- Owner intent for the unexecuted QuantDinger online sidecar card is
  `DATA_MISSING` because no report directory exists.
- A merge-parking registry is not present.
- Whether stale readiness evidence should be preserved after later Strategy Lab
  integration landed needs owner review.

## Next Safe Action

Create a separate exact-allowlist preservation or archive task card. Start with:

`docs/agent_tasks/strategy_lab_quantdinger_complete_and_next_phases_v1_20260524.md`

Reason: it is the QuantDinger-related milestone bundle with an ignored report
directory and an explicit next-safe-task recommendation. Then decide whether
`strategy_lab_quantdinger_readonly_sidecar_online_v1_20260524.md` should be
executed as the next sidecar audit or archived as a draft.

Do not run broad cleanup, `git add -A`, stash, reset, delete, or merge-parking
creation from this audit.

## Project Memory Save Recommendation

Save that on `/home/l4nd0/tenn` at
`0973349937cd42d25d9ea72882d1bd7fc787ce07`, the post-QuantDinger hook dirt was
six foreign untracked task cards plus this audit card, registry `active_jobs`
was empty, merge-parking registry was absent, and the first preservation
candidate is
`strategy_lab_quantdinger_complete_and_next_phases_v1_20260524`.
