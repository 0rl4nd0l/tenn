# Validation

Checked at `2026-06-23T11:39:21Z`.

## Preflight

- `git fetch origin migration/clean-runtime-baseline-reconstruct-v1`: pass.
- Worktree created from current canonical:
  `d2d5b70bb404e0821154f907393f3dfb8dac5896`.
- Portable Tenn git guard preflight:
  pass; `VALID_TASK_WORKTREE`; no active duplicate work.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_hook_status_docs_refresh_v1_20260623.md`: pass.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`:
  pass, no active jobs.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/control_plane_hook_status_docs_refresh_v1_20260623.md --repo-root .`:
  pass.
- PR #402 overlap check:
  no overlap with changed status docs.

## Hook Evidence

- `git config --show-origin --get core.hooksPath`: pass,
  `file:/home/l4nd0/tenn-extraction-handoff-continuation-v1-20260621/.git/config	.githooks`.
- `git rev-parse --git-path hooks`: pass, `.githooks`.
- Strict `scripts/check_agent_hooks.py` for this worktree:
  pass.
- Strict `scripts/check_agent_hooks.py` for `/home/l4nd0/tenn`:
  pass.

## Stale Phrase Search

After edits, this command returned no matches:

```bash
rg -n "/home/l4nd0/tenn/.git/hooks|/mnt/sdb2/.+hooks|common-dir hooks exist|configured path .*missing|Git hook installation check is stale|stale/missing configured path|Fix hook path" docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md docs/dev_flow/CONTROL_PLANE_STATUS.md
```

## Report And Diff Checks

- `python3 -m json.tool reports/agent_jobs/control_plane_hook_status_docs_refresh_v1_20260623/status.json`: pass.
- `bash scripts/check_markdown_hygiene.sh docs/agent_tasks/control_plane_hook_status_docs_refresh_v1_20260623.md docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md docs/dev_flow/CONTROL_PLANE_STATUS.md reports/agent_jobs/control_plane_hook_status_docs_refresh_v1_20260623/README.md reports/agent_jobs/control_plane_hook_status_docs_refresh_v1_20260623/validation.md`: pass.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_hook_status_docs_refresh_v1_20260623.md --repo-root .`: pass.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_hook_status_docs_refresh_v1_20260623.md --repo-root . --no-write-report`: pass before staging.
- `git diff --check`: pass.

## Push Hook Note

Initial `git push -u origin control-plane/hook-status-docs-refresh-v1-20260623`
was blocked by the local `pre-push` hook because this fresh worktree does not
have `financial-engine_v2/.venv/bin/ruff` or
`financial-engine_v2/.venv/bin/pytest`. This task did not create or modify a
runtime/product venv. Push should use the hook-supported
`TENN_ALLOW_MISSING_HOOK_TOOLS=1` bypass after the docs/report validations
above pass; the hook still runs markdown hygiene after the missing-tool bypass.

Final staged checks:

- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_hook_status_docs_refresh_v1_20260623.md --repo-root . --no-write-report`: pass after staging.
- `git diff --cached --check`: pass.
- changed-files versus allowed files: pass; staged files are exactly the task
  card, two status docs, and three report artifacts.

Post-commit check:

- `git status --short --untracked-files=all`: pass, clean.
