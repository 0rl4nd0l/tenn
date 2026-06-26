# Validation

## Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "scribe mode control-plane capture" --json` | 0 | `final_decision=pass`, `path_ownership.classification=VALID_TASK_WORKTREE`, `stop_reimplementation=false`, `registry_status=PASS`, `ledger_status=PASS`; raw output in `guard_portable.json`. |
| `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "scribe mode control-plane capture" --json` | 0 | Same pass result with repo-backed runner; raw output in `guard_repo.json`. |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | `active_jobs=[]`, `read_only=true`; raw output in `registry_readonly.json`. |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | 0 | `ok=true`, `entry_count=34`, `issues=[]`; raw output in `ledger_validate.json`. |
| `python3 scripts/agent_task_ledger.py --repo-root . search --text scribe` | 0 | `ok=true`, `matches=[]`, direct search classification `UNKNOWN_ASK`; raw output in `ledger_search_scribe.json`. |
| `rg -n "scribe|Scribe" docs/agent_tasks reports/agent_jobs .agents/skills docs/dev_flow scripts --hidden --glob '!**/.git/**'` | 0 | Historical/report references plus this task; raw output in `scribe_grep_current.txt`. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md` | 0 | `ok=true`, `issues=[]`. |
| `find .agents/skills -maxdepth 2 -name SKILL.md \| sort` | 0 | 12 repo-backed visible skill entrypoints; no new Scribe skill. |
| `[ ! -d .codex/skills ] \|\| find .codex/skills -maxdepth 2 -name SKILL.md \| sort` | 0 | No output; legacy `.codex/skills` visible entries absent. |
| `find .agents/skills .codex/skills -path '*scribe*' -o -path '*Scribe*' 2>/dev/null \| sort` | 0 | No output; no Scribe skill path exists. |
| `git diff --check` | 0 | No whitespace errors. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md --repo-root .` | 0 | `ok=true`, no disallowed files; raw output in `diff-check.json`. |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md --repo-root .` | 0 | `ok=true`; every allowlisted report artifact exists and is non-empty. |
| `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md --repo-root .` | 0 | `ok=true`; control-plane-only closeout accepted. |
| `git push -u origin safe/scribe-mode-control-plane-v1-20260626` | 1 | Blocked by pre-push hook because `financial-engine_v2/.venv/bin/ruff` and `financial-engine_v2/.venv/bin/pytest` are missing. |
| `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin safe/scribe-mode-control-plane-v1-20260626` | 0 | Owner approved this explicit missing-hook-tool bypass at `2026-06-26T07:01:13Z`; hook skipped lint/test checks, markdown hygiene passed, and branch was pushed. |

## Visible Skill Count

Repo-backed visible skill entries remain 12:

```text
.agents/skills/caveman/SKILL.md
.agents/skills/codex-worker-bridge/SKILL.md
.agents/skills/tenn-explain/SKILL.md
.agents/skills/tenn-financial-metric-extraction/SKILL.md
.agents/skills/tenn-fix/SKILL.md
.agents/skills/tenn-git-guard/SKILL.md
.agents/skills/tenn-goal-report/SKILL.md
.agents/skills/tenn-handoff/SKILL.md
.agents/skills/tenn-improve-codebase-architecture/SKILL.md
.agents/skills/tenn-issue/SKILL.md
.agents/skills/tenn-review-board/SKILL.md
.agents/skills/zoom-out/SKILL.md
```

## DATA_MISSING

- Host picker/autocomplete visibility was not probed; not required by this task.
- Live ledger append was intentionally skipped because it was not approved.
- Repo venv hook tools `ruff` and `pytest` are missing; push uses the explicit
  owner-approved bypass rather than mutating the venv.
