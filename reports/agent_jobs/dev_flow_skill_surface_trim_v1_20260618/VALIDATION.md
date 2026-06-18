# Validation

## Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md` | 0 | Task card valid. |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | `ok: true`, `read_only: true`, `active_jobs: []`. |
| `python3 scripts/agent_task_ledger.py resolve-path` | 0 | Live ledger path resolved under shared registry root. |
| `python3 scripts/agent_task_ledger.py validate` | 0 | Initially `ok: true`, live ledger `DATA_MISSING`, committed ledger present; final rerun `ok: true`, live entry count 2, committed ledger present. |
| `python3 scripts/agent_task_ledger.py append --entry-file reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/handoff/LEDGER_ENTRY.json --fill-identity` | 1 then 0 | First run rejected `validation.status: in_progress`; entry was corrected to `partial`; rerun appended a live `claimed` entry. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md --no-write-report` | 0 | Changed files were inside task-card allowlist. |
| `git diff --check` | 0 | No whitespace errors. |
| Lightweight skill-surface check | 0 | `skill_surface_ok count=10`; removed entrypoints absent and all remaining skill files have H1s. |
| Active removed-entrypoint reference check | 0 | No active `.agents`, `docs/dev_flow`, `docs/agents`, or `scripts` references point to removed `.agents/skills/*/SKILL.md` paths. Historical task cards still mention old paths as evidence and were left unchanged. |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md` | 0 | All report artifacts exist and are non-empty. |
| Product/runtime/data/extraction/count-24 guard | 0 | `forbidden_path_guard_ok`; no forbidden path class changed. |
| Host-global guard | 0 | `host_global_guard_ok`; no host-global or `.codex` config/skill path changed. |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1 --prune` | 0 | Latest canonical resolved to `bae8eda25633cf651849c5681d7ffcb00160fbf9`. |
| Latest-canonical overlap check | 0 | PR #377 changed ledger files only; no overlap with this trim's changed files. |
| Pre-stage `git status --short --untracked-files=all` | 0 | Only task-card-allowed `.agents/skills` and `docs/dev_flow` paths appear; report bundle is ignored and covered by artifact check. |

## Lightweight Validation Contract

- Removed skill entrypoints must be absent:
  - `tenn-auto-progress`
  - `tenn-frame-design`
  - `tenn-git-hygiene`
  - `tenn-worker`
  - `tenn-code-reviewer`
  - `tenn-task-card-registry-safety`
- Active repo skill count should be 10.
- Core skill H1s must still exist for:
  - `tenn-issue`
  - `tenn-fix`
  - `tenn-git-guard`
  - `tenn-goal-report`
  - `tenn-handoff`
  - `tenn-review-board`
  - `tenn-explain`
  - `tenn-financial-metric-extraction`
  - `tenn-improve-codebase-architecture`
  - `codex-worker-bridge`
