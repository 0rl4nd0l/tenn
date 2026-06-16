# Git Hook Install Execution - 2026-06-16

Status: `DONE_WITH_RISK`

## Result

Installed worktree-local, versioned Git hooks and configured this worktree to
use them:

```text
core.hooksPath = .githooks
```

The active effective hook directory is now:

```text
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/.githooks
```

Both required hooks are present, executable, and contain the active-worktree
fingerprint `git rev-parse --show-toplevel`.

## Files Changed In This Pass

- `docs/agent_tasks/git_hook_install_execution_v1_20260616.md`
- `.githooks/pre-commit`
- `.githooks/pre-push`
- `scripts/check_agent_hooks.py`
- `reports/agent_jobs/git_hook_install_execution_v1_20260616/REPORT.md`
- `reports/agent_jobs/git_hook_install_execution_v1_20260616/COMMANDS.md`

`scripts/test_check_agent_hooks.py` was listed in the allowlist but did not need
changes; existing tests covered the checker behavior after the Git-plumbing
patch.

## Non-File Mutation

Ran:

```bash
git config core.hooksPath .githooks
git config --local core.hooksPath /home/l4nd0/tenn/.git/hooks
git config --worktree core.hooksPath .githooks
```

The first command briefly wrote `.githooks` to the common config. I corrected
that by restoring the common config to its prior value and writing the active
hook path to this worktree's `config.worktree`.

Current evidence:

```text
file:/mnt/sdb2/home/l4nd0/tenn/.git/config    /home/l4nd0/tenn/.git/hooks
file:/mnt/sdb2/home/l4nd0/tenn/.git/worktrees/tenn-nvme-clean-baseline-reconstruct-v1/config.worktree    .githooks
git config --show-origin --get core.hooksPath    file:/mnt/sdb2/home/l4nd0/tenn/.git/worktrees/tenn-nvme-clean-baseline-reconstruct-v1/config.worktree    .githooks
git rev-parse --git-path hooks                   .githooks
```

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/git_hook_install_execution_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/check_agent_hooks.py --repo-root . --strict --expect-fingerprint 'pre-commit=git rev-parse --show-toplevel' --expect-fingerprint 'pre-push=git rev-parse --show-toplevel'`
- `financial-engine_v2/.venv/bin/pytest -q scripts/test_check_agent_hooks.py`
- `python3 -m py_compile scripts/check_agent_hooks.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/git_hook_install_execution_v1_20260616.md --repo-root .`
- `.githooks/pre-commit`
- `.githooks/pre-push`

Direct `pre-push` evidence:

```text
[pre-push] ruff check...
All checks passed!
[pre-push] hook/tooling tests...
51 passed in 3.94s
[pre-push] markdown hygiene...
[markdown-hygiene] Internal markdown link scan passed.
```

Follow-up push validation found that Git hook invocations export repository
environment variables into child processes. The hooks now clear Git's local
environment variables from `git rev-parse --local-env-vars` after resolving the
active repo root, before running commands that may create temporary Git repos.

Blocked by unrelated existing checkout dirt:

- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/git_hook_install_execution_v1_20260616.md --repo-root . --no-write-report`

The failure is expected in this shared dirty checkout because prior agent-flow
cleanup files remain modified/untracked outside this hook-install card's
allowlist. I did not clean, revert, stage, stash, or widen the allowlist.

## Unsafe Actions Avoided

- No runtime or service starts.
- No dependency installs.
- No GitHub writes.
- No commits, branch operations, resets, stashes, cleans, merges, rebases, or
  worktree deletion.
- No production data, DB, Qdrant, Redis, model, GPU, or extraction-state
  mutation.

## Next Recommended Step

Resolve the broader shared-checkout dirt from the earlier agent-flow cleanup
wave when you are ready to package or commit this work.
