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
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1` after owner approval | 0 | canonical refreshed to `a299ce45e42f50c23321733082c7d5bbe8dfb88a` |
| `git merge-tree $(git merge-base HEAD origin/migration/clean-runtime-baseline-reconstruct-v1) HEAD origin/migration/clean-runtime-baseline-reconstruct-v1 \| rg -n '<<<<<<<\|changed in both\|CONFLICT\|removed in'` | 1 | no conflict markers or conflict lines found before branch refresh |
| `git merge --no-edit origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | normal branch refresh merge from current canonical; no force-push or rebase |
| `git diff --name-status origin/migration/clean-runtime-baseline-reconstruct-v1...HEAD` after branch refresh | 0 | PR-owned diff remained limited to `AGENTS.md`, task card, and this report bundle |
| `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin HEAD` | 0 | branch pushed; local pre-push skipped missing repo-venv `ruff`/`pytest`, markdown hygiene passed |
| `gh pr create --draft --base migration/clean-runtime-baseline-reconstruct-v1 --head control-plane/agent-docs-project-boundary-routing-v1-20260629 ...` | 0 | draft PR #476 opened: `https://github.com/0rl4nd0l/tenn/pull/476` |
| `gh pr view 476 --json number,state,isDraft,mergeable,mergeStateStatus,commits,statusCheckRollup,url,updatedAt` during review | 0 | draft PR #476 was open, `MERGEABLE`, `CLEAN`; `lint-and-test` and `scan` were `SUCCESS`; latest checked PR commit was `6c015da99f3d52f507cdc81f500a27803a095843` |
| `python3 scripts/tenn_dev_status.py` during fix preflight | 0 | task worktree clean, but guard blocked as `STALE_PATH`; `stop_reimplementation=true` because canonical had advanced |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-agent-docs-project-boundary-routing-v1-20260629 --topic "agent docs project boundary routing update fix" --json` during fix preflight | 0 | `final_decision=block`, `classification=STALE_PATH`, `canonical_head=105b174ba723b978d486e9eebaf10c6ee6bce242`, `merge_base=a299ce45e42f50c23321733082c7d5bbe8dfb88a`, duplicate work `NO_MATCHING_ACTIVE_WORK_FOUND`, registry `PASS`, ledger `PASS` |
| `git merge-tree $(git merge-base HEAD origin/migration/clean-runtime-baseline-reconstruct-v1) HEAD origin/migration/clean-runtime-baseline-reconstruct-v1 \| rg -n '<<<<<<<\|changed in both\|CONFLICT\|removed in'` before fix refresh | 1 | no conflict markers or conflict lines found |
| `git merge --no-edit origin/migration/clean-runtime-baseline-reconstruct-v1` during fix | 0 | normal branch refresh merge from current canonical `105b174ba723b978d486e9eebaf10c6ee6bce242`; merge commit `95677604e1660abc7de62120a3e51b084a8f7c5e`; no force-push or rebase |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md` after fix report edit | 0 | `ok=true`, no issues |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --no-write-report` after fix report edit | 0 | `ok=true`, `disallowed_files=[]`; only `STATE.md` and `VALIDATION.md` were dirty |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --repo-root .` after fix report edit | 0 | `ok=true`, report artifacts present and non-empty |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --repo-root .` after fix report edit | 0 | `ok=true` |
| `git diff --check` after fix report edit | 0 | no whitespace errors |
| `rg -n "Project ownership and external-sibling boundaries\|PROJECT_BOUNDARIES\|external sibling\|not a Tenn subsystem\|external sibling project" AGENTS.md docs/README.md docs/dev_flow/PROJECT_BOUNDARIES.md docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629` after fix report edit | 0 | focused routing terms found in `AGENTS.md`, active source map, boundary doc, task card, and report |
| `python3 scripts/tenn_dev_status.py` after fix report edit | 0 | `GUARD_RESULT=pass`; dirty files were limited to report-local `STATE.md` and `VALIDATION.md`; duplicate work `NO_MATCHING_ACTIVE_WORK_FOUND`, registry `PASS`, ledger `PASS` |

## Guard Notes

The original `/home/l4nd0/tenn` launch worktree had unrelated extraction dirt.
This task did not edit that worktree. A fresh sibling worktree was created from
canonical head `ca424a2835094de40c366a36d4bb0bf04cd8246a`, and guard passed
there before mutation.

After the local docs commit, canonical advanced to
`a299ce45e42f50c23321733082c7d5bbe8dfb88a`. Owner approval was received to
refresh and publish, so the branch was updated with a normal merge commit.

Review then found that the report-local published-head field was stale and that
canonical had advanced again to
`105b174ba723b978d486e9eebaf10c6ee6bce242`. Owner requested `fix`, so the
branch was refreshed again with a normal merge commit. The closeout now avoids a
self-referential `Published head` hash because the report commit itself changes
the branch head; use `gh pr view 476 --json commits` for the live PR head.

## Validation Status

Required docs/control-plane validation passed before local commit and was rerun
after canonical branch refreshes. Draft PR #476 is open. Runtime functionality
is out of scope and was not tested.
