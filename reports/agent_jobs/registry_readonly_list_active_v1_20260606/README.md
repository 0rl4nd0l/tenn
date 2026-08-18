# Registry Read-only List-active v1

Date: 2026-06-06

## Objective

Implement and prove a safe `python3 scripts/agent_job_registry.py list-active
--read-only` mode for Tenn agent registry inspection.

This slice is Repo Hygiene / Control Plane infrastructure only. It does not
change Tenn product, backend, frontend, runtime, data, extraction, prompt,
gold-label, service config, database, Qdrant, news, memory, source PDF, or
backfill behavior.

## Branch / Base / HEAD

- Worktree: `/home/l4nd0/tenn-issue-78-agent-constitution-skills-v1-20260606`
- Branch: `repo-hygiene/registry-readonly-list-active-v1-20260606`
- Base commit: `047b2d94a0ac967e0b28cdfbc9baa10285954727`
- Current pre-commit HEAD: `047b2d94a0ac967e0b28cdfbc9baa10285954727`
- Origin: `https://github.com/0rl4nd0l/tenn.git`

## Evidence Used

- Preserved issue #78 commit `047b2d94`.
- `AGENTS.md` task-card, registry, command-output, and validation policies.
- `.agents/skills/tenn-task-card-registry-safety/SKILL.md`.
- `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md`.
- `reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606/README.md`.
- `scripts/agent_job_registry.py`.
- `scripts/test_agent_job_registry.py`.
- `docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md`.

## Implementation Notes

Preflight found that this clean branch already contained the
`list-active --read-only` CLI flag and internal `read_only` path in
`scripts/agent_job_registry.py`.

This slice therefore avoided duplicating implementation code and instead:

- strengthened focused registry tests to snapshot files, directories, report
  status paths, and mtimes around `list-active --read-only`;
- added a current task card for this exact issue #78 follow-on slice;
- updated stale `AGENTS.md` and repo skill guidance that still described
  `list-active --read-only` as missing;
- validated the read-only behavior with a dependency-free harness because
  `pytest` is not installed in this environment.

## Files Changed

- `AGENTS.md`
- `.agents/skills/tenn-task-card-registry-safety/SKILL.md`
- `docs/agent_tasks/registry_readonly_list_active_v1_20260606.md`
- `scripts/test_agent_job_registry.py`
- `reports/agent_jobs/registry_readonly_list_active_v1_20260606/README.md`

## Tests Added / Changed

Changed `scripts/test_agent_job_registry.py`:

- added `tree_metadata_snapshot()` for file, directory, content, and mtime
  snapshots;
- extended the missing-registry-root read-only test to assert no registry root,
  `.lock`, `.lock/owner.json`, or report tree creation;
- extended the existing-record read-only test to assert registry files,
  registry directory mtimes, report status files, and report directory mtimes
  remain unchanged.

## Commands Run

| Command | Exit | Notes |
| --- | ---: | --- |
| `git status --short --untracked-files=all` | 0 | Target worktree was clean before branch creation. |
| `git switch -c repo-hygiene/registry-readonly-list-active-v1-20260606 047b2d94a0ac967e0b28cdfbc9baa10285954727` | 0 | Created branch from preserved issue #78 commit. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/registry_readonly_list_active_v1_20260606.md` | 0 | New task card validates. |
| `python3 -m pytest scripts/test_agent_job_registry.py -q` | 1 | Not runnable here because `/usr/bin/python3: No module named pytest`; no dependency install performed. |
| Dependency-free temporary registry harness | 0 | Proved read-only mode does not create roots, locks, owner files, status files, or mtime changes. |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | Returned `read_only: true`, `lock_acquired: false`, and no active jobs in the live clean worktree. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/registry_readonly_list_active_v1_20260606.md` | 0 | Task card remained valid after edits. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/registry_readonly_list_active_v1_20260606.md --repo-root .` | 0 | Changed files stayed inside task-card scope. Wrote ignored `diff-check.json`. |
| `python3 -m py_compile scripts/agent_job_registry.py scripts/test_agent_job_registry.py` | 0 | Syntax check passed; created ignored `scripts/__pycache__/`. |
| `git diff --check` | 0 | No whitespace errors. |

Additional staged diff checks are run before commit:

- `git diff --cached --name-only`
- `git diff --cached --stat`
- `git diff --cached --check`
- staged-path allowlist guard
- final `git status --short --untracked-files=all`

## Read-only Non-mutation Proof

The temporary harness created two scenarios:

1. Missing registry root:
   - `TENN_AGENT_REGISTRY_ROOT` pointed to a non-existent temporary path.
   - `list-active --read-only` returned success with no active jobs.
   - The registry root still did not exist afterwards.
   - `.lock` and `.lock/owner.json` did not exist.
   - The repo report tree snapshot remained unchanged.

2. Existing claimed job:
   - A temporary task card was claimed through the normal mutating path.
   - The harness snapshotted registry files, registry directories, report status
     files, and report directories with content and `st_mtime_ns`.
   - `list-active --read-only` returned the active job with `read_only: true`
     and `lock_acquired: false`.
   - Registry snapshots and report status snapshots were byte-for-byte and
     mtime-identical after the read-only command.
   - No `.lock` or `.lock/owner.json` was present afterwards.

## Unsafe Actions Avoided

- No product/backend/frontend/runtime/data/extraction changes.
- No DB, Qdrant, news, memory, source-PDF, prompt, gold-label, service config,
  runtime state, or backfill mutation.
- No dependency installation.
- No broad tests.
- No GitHub issue or PR mutation.
- No push.
- No cleanup, reset, stash, rebase, merge, deletion, or modification of the
  dirty source worktree.

## Remaining Risks

- `pytest` is not installed in this environment, so the pytest test file could
  not be executed through pytest locally.
- The dependency-free harness exercises the core read-only contract, but CI or
  a dev environment with pytest should still run `scripts/test_agent_job_registry.py`.
- This slice does not implement read-only variants for `check-overlap`, claim,
  heartbeat, release, hooks, or broader registry automation.

## Ignored Local Artifacts

- `reports/agent_jobs/registry_readonly_list_active_v1_20260606/diff-check.json`
  was generated by task-card `check-diff` and was not staged.
- `scripts/__pycache__/` was generated by `py_compile` and was not staged.

## Next Recommended Prompt

Run a focused CI-capable validation of `scripts/test_agent_job_registry.py`, then
update or create the follow-on issue for read-only `check-overlap` / task-card
hook alignment without touching product/runtime/extraction surfaces.
