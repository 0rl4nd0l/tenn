# Validation

## Commands

| Command | Status | Notes |
| --- | --- | --- |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "AGENTS.md constitutional cleanup" --json` | PASS | Fresh worktree classified `VALID_TASK_WORKTREE`; final decision `pass`. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agents_constitution_slim_v1_20260628.md` | PASS | Task card metadata valid. |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | PASS | No active jobs. |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | PASS | Live and committed ledgers valid. |
| `python3 scripts/check_runtime_functionality_proof_docs.py` | PASS | Runtime proof section present with all required fields. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .` | PASS | Changed paths inside `allowed_files`. |
| `git diff --check` | PASS | No whitespace errors. |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .` | PASS | Docs-only closeout accepted. |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .` | PASS | Listed report artifacts exist and are non-empty. |
| `git status --short --untracked-files=all` | PASS | Only allowed tracked docs and the new task card are visible; report artifacts are ignored by repo policy. |
| `git push -u origin control-plane/agents-constitution-slim-v1-20260628` | BLOCKED_THEN_PASS | First blocked by missing local `ruff`/`pytest`; pushed with documented `TENN_ALLOW_MISSING_HOOK_TOOLS=1` after docs-only validation passed. |
| `gh pr create --draft --base migration/clean-runtime-baseline-reconstruct-v1 --head control-plane/agents-constitution-slim-v1-20260628` | PASS | Opened PR #462. |
| `gh pr view 462 --json number,title,state,isDraft,url,baseRefName,headRefName,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,commits` | PASS | PR open draft; mergeable; `scan` success; `lint-and-test` in progress. |
| PR review | BLOCKED_THEN_FIXED | Found stale report wording claiming no GitHub writes after PR creation. Report and task card now record later user approval for push/PR/branch refresh. |
| `git merge --no-edit origin/migration/clean-runtime-baseline-reconstruct-v1` | PASS | Refreshed branch against canonical `265a0d5a8125254c099e391087724097d6200517` without conflicts. |
| `gh pr view 462 --json number,state,isDraft,mergeable,mergeStateStatus,statusCheckRollup,url,commits` | PASS | Pre-refresh recheck: PR open draft; `scan` success; `lint-and-test` success; mergeable `CONFLICTING`; merge state `DIRTY`. |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "PR #462 AGENTS constitution slim conflict refresh" --json` | EXPECTED_BLOCK | Guard reported `STALE_PATH` against canonical `b2adf891096f41d4ddef260b1c47fd9b5a8417a4`; owner had approved this exact refresh. |
| `git merge --no-edit origin/migration/clean-runtime-baseline-reconstruct-v1` | CONFLICT_THEN_FIXED | Auto-merged operator docs; `AGENTS.md` conflicted and was resolved manually. |
| `rg -n "<<<<<<<|=======|>>>>>>>" AGENTS.md docs/dev_flow/CODEX_OPERATOR_GUIDE.md docs/dev_flow/SKILLS_SURFACE.md` | PASS | No conflict markers remain. |
| `wc -l -c AGENTS.md` | PASS | Resolved file is 241 lines / 12005 bytes. |
| `git diff --cached --name-only origin/migration/clean-runtime-baseline-reconstruct-v1` | PASS | In-merge diff against current canonical was limited to task-card `allowed_files`. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .` | EXPECTED_PRECOMMIT_FAIL | While the merge was uncommitted, `git status` still listed current-base files staged from the merge, so this status-based check reported outside-allowlist base files. |
| `git commit -m "docs(control-plane): refresh constitution PR branch"` | PASS | Created merge commit `93cbfbb4`; pre-commit skipped missing local runtime `ruff`. |
| `git diff --name-only origin/migration/clean-runtime-baseline-reconstruct-v1...HEAD` | PASS | Post-merge PR diff limited to task-card `allowed_files`. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .` | PASS | Post-merge allowed-diff gate passed and refreshed `diff-check.json`. |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .` | PASS | Docs-only closeout accepted. |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .` | PASS | Listed report artifacts exist and are non-empty. |

## Runtime Validation

Skipped by design. This task is docs-only and does not claim runtime
functionality.
