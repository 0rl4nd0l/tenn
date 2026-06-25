# Control Plane Hook Status Docs Refresh

Job id: `control_plane_hook_status_docs_refresh_v1_20260623`

Status: complete; validation passed.

Task card:
`docs/agent_tasks/control_plane_hook_status_docs_refresh_v1_20260623.md`

## Repo State

- Worktree:
  `/home/l4nd0/tenn-control-plane-hook-status-docs-refresh-v1-20260623`
- Branch:
  `control-plane/hook-status-docs-refresh-v1-20260623`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base commit:
  `d2d5b70bb404e0821154f907393f3dfb8dac5896`
- Checked at:
  `2026-06-23T11:39:21Z`

## Scope

Changed only:

- `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`
- `docs/dev_flow/CONTROL_PLANE_STATUS.md`
- this task card and report bundle

Did not change hook scripts, `.githooks`, `.codex`, `.claude`, `.agents`,
runtime/product/data/extraction files, CI, production data, or Git config.

## Live PR State

- PR #399 merged at `2026-06-23T10:35:53Z`, merge commit
  `43df758d57280408f3d2c2567772ae2add90b36b`.
- PR #400 merged at `2026-06-23T11:19:59Z`, merge commit
  `d2d5b70bb404e0821154f907393f3dfb8dac5896`.
- PR #402 is open and mergeable, but its diff is limited to
  `tenn-git-guard` script/tests plus its own task/report artifacts. It does not
  touch the status docs edited here.

## Hook Evidence

Current linked worktree family:

```text
git config --show-origin --get core.hooksPath
file:/home/l4nd0/tenn-extraction-handoff-continuation-v1-20260621/.git/config	.githooks
```

Strict hook validation passes in this fresh worktree with:

```bash
python3 scripts/check_agent_hooks.py --repo-root . --strict \
  --expect-fingerprint 'pre-commit=git rev-parse --show-toplevel' \
  --expect-fingerprint 'pre-push=git rev-parse --show-toplevel'
```

The same strict checker also passes for `/home/l4nd0/tenn`.

## Corrected Stale Claims

`docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`:

- Changed the hook item from stale/partial repair-needed wording to current
  `IMPLEMENTED` status.
- Removed the exact obsolete cross-repo hook path mismatch text.
- Removed hook repair from the recommended fix order.

`docs/dev_flow/CONTROL_PLANE_STATUS.md`:

- Updated the status header to current baseline `d2d5b70b`.
- Replaced the `tenn-git-guard` known-gap hook stale note with a host-local
  Git config caveat.
- Changed Git pre-commit/pre-push hooks from `PARTIAL` to `IMPLEMENTED`.
- Updated the truth-table hook row from stale/missing configured path to strict
  checker passing with `core.hooksPath=.githooks`.

## Docs Impact

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`:
  `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`,
  `docs/dev_flow/CONTROL_PLANE_STATUS.md`,
  `docs/dev_flow/SKILLS_SURFACE.md`,
  `scripts/check_agent_hooks.py`,
  `.githooks/pre-commit`,
  `.githooks/pre-push`
- `docs_changed`:
  `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`,
  `docs/dev_flow/CONTROL_PLANE_STATUS.md`
- `docs_followup`:
  `SKILLS_SURFACE.md` metadata now predates PR #400, but hook-status cleanup did
  not change skill routing or skill files. Refresh only in a separate
  skill-surface freshness task.
- `reason`:
  current live status docs no longer surface obsolete hook-path repair claims.

## Next Narrow Candidate

The next narrow candidate is `/goal monitor` contract cleanup: either document
the host-only `codex-goal-monitor` as permanent HOST_ONLY behavior or create a
separate repo-wrapper/report-protocol task if owner wants repo-backed monitor
semantics.
