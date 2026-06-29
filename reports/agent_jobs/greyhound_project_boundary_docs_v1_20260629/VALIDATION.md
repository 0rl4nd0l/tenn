# Validation

## Commands Run

| Command | Exit | Result |
| --- | ---: | --- |
| `pwd` | 0 | `/home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629` |
| `git branch --show-current` | 0 | `docs/greyhound-project-boundary-v1-20260629` |
| `git rev-parse HEAD` | 0 | `3b32b8b3be8b04bb5a198c71ec928db182438f17` |
| `git rev-parse --abbrev-ref --symbolic-full-name @{u}` | 0 | `origin/migration/clean-runtime-baseline-reconstruct-v1` |
| `python3 scripts/tenn_dev_status.py` before edits | 0 | clean fresh task worktree, guard `pass`, `VALID_TASK_WORKTREE` |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629 --topic "Greyhound external sibling project docs boundary" --json` before edits | 0 | `final_decision=pass`, `VALID_TASK_WORKTREE`, `stop_reimplementation=false`, duplicate work `NO_MATCHING_ACTIVE_WORK_FOUND`, registry `PASS`, ledger `PASS` |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md` | 0 | `ok=true`, no issues |
| `rg -n "Greyhound\|external sibling\|not a Tenn subsystem\|PROJECT_BOUNDARIES\|physical Greyhound relocation\|Runtime Functionality Proof" docs/README.md docs/dev_flow/PROJECT_BOUNDARIES.md docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md` | 0 | focused boundary terms found in allowed docs/task-card surfaces |
| `git diff --check` | 0 | no whitespace errors |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --no-write-report` | 0 | `ok=true`, `disallowed_files=[]` |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | `ok=true`, `active_jobs=[]` |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | 0 | `ok=true`, live and committed ledger sources checked |
| `git diff --name-only HEAD..origin/migration/clean-runtime-baseline-reconstruct-v1 -- docs/README.md docs/dev_flow/PROJECT_BOUNDARIES.md docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md` | 0 | no output; no canonical overlap in allowed docs files |
| `git diff --stat HEAD..origin/migration/clean-runtime-baseline-reconstruct-v1 -- docs/README.md docs/dev_flow/PROJECT_BOUNDARIES.md docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md` | 0 | no output; no canonical overlap in allowed docs files |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --repo-root .` | 0 | `ok=true`, four report artifacts present and non-empty |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --repo-root .` | 0 | `ok=true` |
| `git status --short --untracked-files=all` | 0 | `M docs/README.md`; untracked task card and project-boundary doc |
| `git status --short --ignored --untracked-files=all reports/agent_jobs/greyhound_project_boundary_docs_v1_20260629` | 0 | four ignored report-local closeout files |
| `gh --version` | 0 | GitHub CLI available |
| `gh auth status` | 0 | authenticated to `github.com` as `0rl4nd0l` |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1` | 0 | refreshed canonical branch evidence |
| `git diff --name-only HEAD..origin/migration/clean-runtime-baseline-reconstruct-v1 -- <task allowed docs files>` | 0 | no output; no canonical overlap before rebase |
| `git commit -m "docs: codify Greyhound project boundary"` | 0 | local docs commit created |
| `git rebase origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | single docs commit rebased onto current canonical |
| `python3 scripts/tenn_dev_status.py` after rebase | 0 | clean task worktree, guard `pass`, `VALID_TASK_WORKTREE` |
| `git push -u origin docs/greyhound-project-boundary-v1-20260629` | 1 | blocked by pre-push hook: missing `ruff` and `pytest` in `financial-engine_v2/.venv`; hook says `TENN_ALLOW_MISSING_HOOK_TOOLS=1` can bypass intentionally |

## Guard Notes

The first post-edit explicit guard returned `final_decision=block` with
`DIRTY_RELATED_WORKTREE` because the intended allowed docs files were dirty and
the canonical ref had advanced. This is recorded as residual risk, not hidden.
The diff contract check confirmed the dirty files are inside the task-card
allowlist. After approved publication began, the docs commit was rebased onto
the current canonical ref and `tenn_dev_status.py` returned `VALID_TASK_WORKTREE`.

## Validation Status

All required docs/control-plane validation completed. Runtime functionality was
not tested or proven because this task did not touch runtime systems.

Publication is waiting on owner approval for the missing-hook-tool bypass or a
separate tooling repair path.
