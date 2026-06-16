---
job_id: agent_flow_cleanup_execution_v1_20260616
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/agent_flow_cleanup_execution_v1_20260616
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md
  - .claude/settings.json
  - scripts/agent_job_hook.py
  - scripts/test_agent_job_hook.py
  - scripts/check_agent_hooks.py
  - scripts/test_check_agent_hooks.py
  - scripts/agent_job_contract.py
  - scripts/test_agent_job_contract.py
  - scripts/sync_codex_skills.sh
  - docs/agents/skill-registry.md
  - AGENTS.md
  - CLAUDE.md
  - CODEX.md
  - GEMINI.md
  - financial-engine_v2/PROJECT_AGENT_RULES.md
  - docs/entrypoints.md
  - docs/claude/commands.md
  - docs/claude/gap-analysis.md
  - docs/process/codex_skill_sources/github_issue_system/README.md
  - docs/process/codex_skill_sources/github_issue_system/tenn-issue-closeout/SKILL.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
  - .agents/skills/tenn-git-hygiene/SKILL.md
  - .agents/skills/tenn-auto-progress/SKILL.md
  - reports/agent_jobs/agent_flow_cleanup_execution_v1_20260616/REPORT.md
  - reports/agent_jobs/agent_flow_cleanup_execution_v1_20260616/COMMANDS.md
  - reports/agent_jobs/agent_flow_cleanup_execution_v1_20260616/SELF_REVIEW.md
  - reports/agent_jobs/agent_flow_cleanup_execution_v1_20260616/SUBAGENT_REVIEW.md
---

# Agent Flow Cleanup Execution V1

## Objective

Execute the four remaining agent-flow cleanup items:

1. Add a read-only Git hook status checker.
2. Normalize skill authority around `.agents/skills`.
3. Collapse identity instruction docs back to `AGENTS.md` as the constitution.
4. Add report-bundle artifact validation to task-card tooling.

## Scope

Allowed:

- Control-plane docs, hook wrapper/config/tests, task-card tooling/tests, and
  repo-backed skill instruction edits listed in `allowed_files`.
- Read-only reviewer subagents.
- Report-local closeout artifacts under the configured output directory.

Forbidden:

- Product/runtime/extraction/data/code changes outside the allowlist.
- Host hook sync, host `$CODEX_HOME` mutation, host Git config mutation, or
  installing hooks.
- Runtime/service starts, dependency installs, DB/Qdrant/Redis/news/memory/
  backfill/source-PDF/gold-label/model/GPU mutation.
- GitHub writes, commit, push, merge, rebase, cherry-pick, reset, stash, clean,
  branch deletion, or worktree deletion.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 -m py_compile scripts/agent_job_hook.py scripts/check_agent_hooks.py scripts/agent_job_contract.py`
- `python3 -m json.tool .claude/settings.json`
- focused pytest for hook, hook-status, and contract tests
- `git diff --check`
- task-card `check-diff --no-write-report`, with unrelated pre-existing dirt
  recorded instead of cleaned or allowlist-widened
