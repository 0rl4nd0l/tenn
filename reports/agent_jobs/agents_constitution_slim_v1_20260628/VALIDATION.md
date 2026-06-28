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

## Runtime Validation

Skipped by design. This task is docs-only and does not claim runtime
functionality.
