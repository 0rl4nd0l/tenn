# Validation

All commands were run from
`/home/l4nd0/tenn-skill-surface-freshness-semantics-v1-20260626`.

| Command | Result |
| --- | --- |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-skill-surface-freshness-semantics-v1-20260626 --topic "skill surface freshness semantics" --json` | pass |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "skill surface freshness semantics" --json` | pass |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/skill_surface_freshness_semantics_v1_20260626.md` | pass |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass; no active jobs |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | pass; 32 entries after claim append |
| `find .agents/skills -maxdepth 2 -name SKILL.md \| sort` | pass; 12 entries |
| `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md \| sort` | pass; 0 entries |
| `git merge-base --is-ancestor b3b3a154590f36e61d297c1ac79fe623526f0b28 origin/migration/clean-runtime-baseline-reconstruct-v1` | pass; exit 0 |
| `git diff --check` | pass |
| `uv run --with pytest --with pyyaml pytest tests/test_agent_task_ledger.py` | pass; 24 passed, 1 existing warning |

Contract closeout checks are run after report artifact creation.

## DATA_MISSING

Host picker/autocomplete visibility was not probed.
