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
| `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin docs/greyhound-project-boundary-v1-20260629` | 0 | owner-approved one-shot bypass for missing local hook tools; branch pushed |
| `gh pr create --draft ...` | 0 | draft PR #472 opened: `https://github.com/0rl4nd0l/tenn/pull/472` |
| `gh pr view 472 --json number,title,state,isDraft,headRefName,baseRefName,mergeable,mergeStateStatus,statusCheckRollup,url,updatedAt,commits` | 0 | PR open, draft, mergeable, merge state `CLEAN`; `lint-and-test=SUCCESS`, `scan=SUCCESS`; head `7af1c2dceaa91b5d0f3ff7e1751d690902f3e5da` |
| `python3 scripts/tenn_dev_status.py` before closeout fix | 0 | clean task worktree, guard `pass`, `VALID_TASK_WORKTREE` |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629 --topic "greyhound project boundary docs closeout fix" --json` before closeout fix | 0 | `final_decision=pass`, `VALID_TASK_WORKTREE`, `stop_reimplementation=false`, duplicate work `NO_MATCHING_ACTIVE_WORK_FOUND`, registry `PASS`, ledger `PASS` |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md` after closeout fix | 0 | `ok=true`, no issues |
| `python3 scripts/tenn_dev_status.py` after closeout fix, before follow-up commit | 0 | dirty docs/report files only; guard runner available; registry `PASS`; ledger `PASS` |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629 --topic "greyhound project boundary docs closeout fix" --json` after closeout fix, before follow-up commit | 0 | dirty allowed docs/report files caused `final_decision=block`; this was paired with `check-diff` below |
| `bash -lc 'if rg -n "WAITING_ON_[U]SER\|Publication is waitin[g]\|branch push is blocked unti[l]\|Recommended next prompt to finish publicatio[n]" reports/agent_jobs/greyhound_project_boundary_docs_v1_20260629 docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md docs/dev_flow/PROJECT_BOUNDARIES.md; then exit 1; fi'` | 0 | no stale wait-state closeout phrases remain |
| `rg -n "Greyhound\|external sibling\|not a Tenn subsystem\|PROJECT_BOUNDARIES\|Publish refresh canonical parent\|PR_OPEN_DRAFT_CLOSEOUT_CORRECTED" docs/README.md docs/dev_flow/PROJECT_BOUNDARIES.md docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md reports/agent_jobs/greyhound_project_boundary_docs_v1_20260629` | 0 | focused boundary and closeout terms found only in allowed docs/report surfaces |
| `git diff --check` after closeout fix | 0 | no whitespace errors |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --no-write-report` after closeout fix | 0 | `ok=true`, `disallowed_files=[]` |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --repo-root .` after closeout fix | 0 | `ok=true`, four report artifacts present and non-empty |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --repo-root .` after closeout fix | 0 | `ok=true` |

## Guard Notes

The first post-edit explicit guard returned `final_decision=block` with
`DIRTY_RELATED_WORKTREE` because the intended allowed docs files were dirty and
the canonical ref had advanced. This is recorded as residual risk, not hidden.
The diff contract check confirmed the dirty files are inside the task-card
allowlist. After approved publication began, the docs commit was rebased onto
the current canonical ref and `tenn_dev_status.py` returned `VALID_TASK_WORKTREE`.

The closeout-fix dirty guard also returned a dirty-worktree block before the
follow-up commit because the intended report/doc files were modified. The
task-card diff contract again confirmed `disallowed_files=[]`.

## Validation Status

All required docs/control-plane validation completed. Runtime functionality was
not tested or proven because this task did not touch runtime systems.

Publication reached draft PR #472 after owner approval for the one-shot missing
local hook tool bypass. At closeout-fix start, the PR was open, draft,
mergeable, and green. No merge, mark-ready action, runtime validation, or
Greyhound mutation was performed.
