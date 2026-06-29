# Validation

## Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/tenn_dev_status.py` before edits | 0 | clean task worktree, guard pass, `VALID_TASK_WORKTREE`, `stop_reimplementation=false` |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-agent-docs-project-boundary-routing-v1-20260629 --topic "agent docs project boundary routing update" --json` before edits | 0 | `final_decision=pass`, `VALID_TASK_WORKTREE`, duplicate work `NO_MATCHING_ACTIVE_WORK_FOUND`, registry `PASS`, ledger `PASS` |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md` | 0 | `ok=true`, no issues |
| `rg -n "Project ownership and external-sibling boundaries\|PROJECT_BOUNDARIES\|external sibling\|not a Tenn subsystem" AGENTS.md docs/README.md docs/dev_flow/PROJECT_BOUNDARIES.md docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629` | 0 | focused routing terms found in `AGENTS.md`, active source map, boundary doc, task card, and report |
| `git diff --check` | 0 | no whitespace errors |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --no-write-report` | 0 | `ok=true`, `disallowed_files=[]` |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --repo-root .` | 0 | `ok=true`, three report artifacts present and non-empty |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --repo-root .` | 0 | `ok=true` |
| `git status --short --untracked-files=all` before commit | 0 | `M AGENTS.md`; task card untracked; report files ignored until explicitly added |

## Guard Notes

The original `/home/l4nd0/tenn` launch worktree had unrelated extraction dirt.
This task did not edit that worktree. A fresh sibling worktree was created from
canonical head `ca424a2835094de40c366a36d4bb0bf04cd8246a`, and guard passed
there before mutation.

## Validation Status

Required docs/control-plane validation passed before local commit. Runtime
functionality is out of scope and was not tested.
