# State

Generated: 2026-06-29T20:28:37+1000

## Result

Status: `DRAFT_PR_OPEN_REFRESHED`

The Tenn agent docs update is implemented in a fresh task worktree:

- Worktree:
  `/home/l4nd0/tenn-agent-docs-project-boundary-routing-v1-20260629`
- Branch: `control-plane/agent-docs-project-boundary-routing-v1-20260629`
- Base HEAD: `ca424a2835094de40c366a36d4bb0bf04cd8246a`
- First refreshed canonical parent:
  `a299ce45e42f50c23321733082c7d5bbe8dfb88a`
- First branch refresh merge commit:
  `ba261c9bbad02ade4486dd712c420606a940cb70`
- Draft PR head checked during review:
  `6c015da99f3d52f507cdc81f500a27803a095843`
- Current canonical parent for this fix:
  `105b174ba723b978d486e9eebaf10c6ee6bce242`
- Current branch refresh merge commit:
  `95677604e1660abc7de62120a3e51b084a8f7c5e`
- Current PR head:
  use `gh pr view 476 --json commits` or `git rev-parse HEAD` after push;
  this report does not hard-code the hash of the commit that contains itself.
- Draft PR: `https://github.com/0rl4nd0l/tenn/pull/476`
- Scope: docs-only control-plane routing

`AGENTS.md` now routes project ownership and external-sibling boundary
questions to `docs/dev_flow/PROJECT_BOUNDARIES.md`.

After owner approval, the branch was refreshed against current canonical with
normal merge commits. The PR-owned diff against
`origin/migration/clean-runtime-baseline-reconstruct-v1` remained limited to the
task-card allowed files after each refresh.

After owner approval, the branch was pushed and opened as draft PR #476. Review
then found stale report metadata and a newer canonical parent, so this closeout
was refreshed. No merge was performed.

## Source Worktree Note

`/home/l4nd0/tenn` had unrelated dirty extraction files when this task started:

- `docs/agent_tasks/extraction_qbe_revenue_selection_v1_20260629.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`

Those files were not touched, staged, committed, cleaned, or moved by this
task. The agent-docs update was isolated in the fresh sibling worktree listed
above.

## Files Touched

- `AGENTS.md`
- `docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md`
- `reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629/STATE.md`
- `reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629/VALIDATION.md`
- `reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629/NEXT_GOAL.md`

## Files Intentionally Not Touched

- Tenn product/runtime/backend/extraction/parser/evaluator files.
- Greyhound repo files, DBs, systemd units, services, runtime artifacts,
  branches, worktrees, or GitHub surfaces.
- `/home/l4nd0/tenn` dirty extraction files.
- `docs/dev_flow/PROJECT_BOUNDARIES.md`, because it already contains the
  detailed boundary rule and did not need a content change.
- `docs/README.md`, because it already routes to `PROJECT_BOUNDARIES.md`.

## Docs Impact

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`,
  `docs/dev_flow/PROJECT_BOUNDARIES.md`, `.agents/skills/tenn-fix/SKILL.md`
- `docs_changed`: `AGENTS.md`
- `docs_followup`: `none`
- `reason`: the root agent constitution now links to the active
  project-boundary guide without duplicating its detailed rules.

## Functionality Proof

This was docs-only control-plane work. Tenn runtime functionality and Greyhound
runtime functionality were not tested or proven.

## Unsafe Actions Avoided

- No service start, stop, restart, or unit rewrite.
- No runtime, DB, data, source-PDF, gold-label, prompt, Docker, dependency, or
  model mutation.
- No Greyhound repo mutation.
- No service, runtime, data, Greyhound, cleanup, branch deletion, worktree
  deletion, pruning, parked-work, reset, stash, force-push, or rebase action.
- A normal branch refresh merge from canonical was performed after owner
  approval; GitHub mutation was limited to branch push and draft PR creation for
  this docs-only branch.
