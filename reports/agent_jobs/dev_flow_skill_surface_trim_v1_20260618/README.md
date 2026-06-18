# Dev Flow Skill Surface Trim V1

State: READY_FOR_PR

## Objective

Continue the Tenn/Codex skill context bloat trim from fresh canonical
`acb7e9a7df6a9b75d14beff16c750693a4aab5e6`, using the preserved
`reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/` audit bundle.
Canonical was refreshed before commit/PR follow-through; latest
`origin/migration/clean-runtime-baseline-reconstruct-v1` is
`bae8eda25633cf651849c5681d7ffcb00160fbf9`.

## Current State

- Worktree: `/home/l4nd0/tenn-dev-flow-skill-surface-trim-v1-20260618`
- Branch: `control-plane/dev-flow-skill-surface-trim-v1-20260618`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base/HEAD at start: `acb7e9a7df6a9b75d14beff16c750693a4aab5e6`
- Latest canonical at pre-PR validation:
  `bae8eda25633cf651849c5681d7ffcb00160fbf9`.
- Overlap with latest canonical changes: none; PR #377 changed ledger files
  outside this trim's task-card allowlist.
- Upstream: `DATA_MISSING` until this local branch is pushed.
- Registry: read-only `ok: true`, `active_jobs: []`.
- Ledger: live ledger was initially `DATA_MISSING`; a live claimed entry was
  appended with `scripts/agent_task_ledger.py`.
- PR #375: `MERGED` into canonical at `acb7e9a7df6a...`.
- PR #367: `OPEN`, classified `SUPERSEDED_IGNORE` by #375 for this lane; not
  merged, updated, or adopted.

## What Changed

- Reduced visible repo skill entrypoints from 16 to 10 by deleting six
  auxiliary `SKILL.md` files:
  - `.agents/skills/tenn-auto-progress/SKILL.md`
  - `.agents/skills/tenn-frame-design/SKILL.md`
  - `.agents/skills/tenn-git-hygiene/SKILL.md`
  - `.agents/skills/tenn-worker/SKILL.md`
  - `.agents/skills/tenn-code-reviewer/SKILL.md`
  - `.agents/skills/tenn-task-card-registry-safety/SKILL.md`
- Rehomed the still-useful behavior into:
  - `.agents/skills/tenn-issue/SKILL.md`
  - `.agents/skills/tenn-fix/SKILL.md`
  - `.agents/skills/tenn-git-guard/SKILL.md`
  - `.agents/skills/tenn-goal-report/SKILL.md`
  - `docs/dev_flow/SKILLS_SURFACE.md`
  - `docs/dev_flow/templates/FRAME.md`
  - `docs/dev_flow/templates/OPERATOR_NOTES.md`
  - worker and PR-review templates

## Files Touched

- `docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md`
- `.agents/skills/tenn-issue/SKILL.md`
- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-git-guard/SKILL.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `.agents/skills/tenn-improve-codebase-architecture/SKILL.md`
- deleted `.agents/skills/tenn-auto-progress/SKILL.md`
- deleted `.agents/skills/tenn-frame-design/SKILL.md`
- deleted `.agents/skills/tenn-git-hygiene/SKILL.md`
- deleted `.agents/skills/tenn-worker/SKILL.md`
- deleted `.agents/skills/tenn-code-reviewer/SKILL.md`
- deleted `.agents/skills/tenn-task-card-registry-safety/SKILL.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `docs/dev_flow/templates/FRAME.md`
- `docs/dev_flow/templates/OPERATOR_NOTES.md`
- `docs/dev_flow/templates/WORKER_TASK.md`
- `docs/dev_flow/templates/WORKER_RESULT.md`
- `docs/dev_flow/templates/PR_REVIEW.md`
- `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/*`

## Files Intentionally Not Touched

- Tenn product, runtime, data, extraction, source-PDF, gold-label, prompt,
  schema, service, model, GPU, DB, Qdrant, Redis, news, memory, and count-24
  paths.
- Host-global skill/config roots under `/home/l4nd0/.codex` and
  `/home/l4nd0/.agents`.
- PR #367 branch and worktree.
- GitHub state.

## Validation

See `VALIDATION.md`.

## DATA_MISSING And Remaining Risk

- Upstream is `DATA_MISSING` because the local branch has not been pushed.
- Live skill-loader behavior is inferred from the file surface; this run did
  not start a fresh Codex session to prove the deleted `SKILL.md` files vanish
  from the next session's advertised skills.
- The implementation is ready for local commit and focused PR creation under
  the owner's explicit follow-through instruction.

## Unsafe Actions Avoided

- Did not merge, update, or close PR #367.
- Did not mutate GitHub before explicit owner approval to push/open a focused
  PR.
- Did not clean, reset, stash, rebase, cherry-pick, delete branches, remove
  worktrees, prune, or force-push.
- Did not install dependencies, start services, or touch runtime/data/product
  surfaces.

## Ignored Artifact Note

`reports/` is ignored in this repo. The report bundle and handoff files are
present on disk but require `git add -f reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/...`
if this branch is committed.

## Next Recommended Prompt

Commit the local diff, push
`control-plane/dev-flow-skill-surface-trim-v1-20260618`, and open a focused PR
against `migration/clean-runtime-baseline-reconstruct-v1`.
